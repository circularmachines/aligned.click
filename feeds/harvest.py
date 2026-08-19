"""Keyword harvesting and indexing — turning a criteria into an embedded pool.

The reader's literal answer (the criteria) is embedded and cosine-searched
against the global keyword store (index_db.keywords); the top similar terms are
shown to the harvest call so it builds on what is already known instead of
re-proposing it. The system prompt is a fixed constant — byte-identical on
every call, so the provider can cache it; the criteria and the similar terms
travel in the user message.

**Indexing a keyword** now means embedding all of its posts from the last
FEEDS_WINDOW_DAYS, capped at KEYWORD_POST_CAP (state.py). A keyword whose
last-month supply exceeds the cap is disqualified: it is too common to be a
useful retrieval signal — a term like "the" can never be indexed. The embedded
posts are the corpus the per-post judge is seeded from (pipeline.py).

The chat call talks to GreenPT v4 flash through cause/classify's _completion,
the same transport the product uses everywhere; embeddings use feeds/embed.py.
"""

import datetime
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
sys.path.insert(0, str(ROOT.parent / "index"))
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT))

import state  # noqa: E402
import apppass  # noqa: E402
import embed  # noqa: E402
import index_db  # noqa: E402
import judge  # noqa: E402
from classify import ClassifyError, _completion, _find_json_array  # noqa: E402
from post_index import extract  # noqa: E402

# The static system prompt — identical on every call so the provider can cache
# the prefix. The criteria and the similar keywords live in the user message.
HARVEST_SYSTEM = (
    "You give a Bluesky feed new search terms. Given what the reader asked to "
    "see and the search terms already indexed for similar requests, name 1-3 "
    "word search terms (lowercase, no quotes) that would retrieve that kind of "
    "post.\n"
    "How a term is matched, exactly: a single word is searched as that word; "
    "a multi-word term is searched as the exact phrase in that order — it "
    "does NOT match posts that only contain some of those words. There is no "
    "OR-ing and no word-by-word matching. So a term like \"repair cafe\" "
    "retrieves posts containing the phrase \"repair cafe\", and a term like "
    "\"mending\" retrieves posts containing that word. Name phrases that "
    "genuinely occur together in that order; when in doubt, prefer a good "
    "single word.\n"
    "Do not repeat any term already on the indexed list. Skip anything too "
    "common to be a useful search — a term like \"the\" or \"news\" matches "
    "far too many posts and gets disqualified. Skip brand names and specific "
    "places."
)


def _similar_block(similar: list[dict]) -> str:
    """The already-known terms as a prompt block, with their status so the
    model sees both what works and what was disqualified."""
    if not similar:
        return ""
    lines = "\n".join(
        f"- {s['keyword']} ({s['status']}"
        + (f", {s['post_count']} posts last month)" if s.get("post_count") else ")")
        for s in similar)
    return ("Search terms already in the index for similar requests "
            "(do not repeat these):\n" + lines + "\n\n")


def harvest(criteria: str, similar: list[dict]) -> list[str]:
    """The first LLM action for a criteria: new search terms.

    `similar` is the top cosine matches in the global keyword store. First use
    of the feature has none — the call works from the criteria alone.
    """
    user = (_similar_block(similar)
            + f"The request: {criteria}\n\n"
              "Return ONLY a JSON array of search terms, 4 to 8 of them. "
              "No prose around the JSON.")
    for attempt in range(3):
        try:
            content = _completion([
                {"role": "system", "content": HARVEST_SYSTEM},
                {"role": "user", "content": user},
            ])
            return _parse_terms(content)
        except ClassifyError as e:
            if attempt == 2:
                raise
            continue


def _parse_terms(content: str) -> list[str]:
    try:
        terms = json.loads(_find_json_array(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"terms JSON did not parse ({e})") from None
    if not isinstance(terms, list):
        raise ClassifyError("terms call returned an object, not an array")
    cleaned: list[str] = []
    for t in terms:
        if not isinstance(t, str):
            continue
        t = t.strip().strip('"').lower()
        if 1 < len(t) <= 40 and t not in cleaned:
            cleaned.append(t)
    return cleaned


# --- indexing a keyword -------------------------------------------------------


def _collect_posts(term: str, cap: int, cutoff: datetime.datetime) -> list[dict]:
    """The term's last-month posts, paginated, newest first. Stops early at the
    first post older than the window (search is newest-first), and stops at
    cap+1 — enough to know the term is too common without reading every page."""
    from search_posts import build_query
    query = build_query([term])
    collected: list[dict] = []
    cursor = None
    while len(collected) <= cap:
        params = {"q": query, "sort": "latest", "limit": 100}
        if cursor:
            params["cursor"] = cursor
        if apppass.configured():
            page = apppass.xrpc_get("app.bsky.feed.searchPosts", params)
        else:
            from bsky import get
            page = get("app.bsky.feed.searchPosts", params)
        views = page.get("posts") or []
        if not views:
            break
        for v in views:
            when = judge.parse_created(((v.get("record") or {}).get("createdAt") or ""))
            if when is None:
                continue
            if when < cutoff:
                return collected
            collected.append(v)
            if len(collected) > cap:
                return collected
        cursor = page.get("cursor")
        if not cursor:
            break
    return collected


def index_keywords(terms: list[str], provenance: str) -> list[dict]:
    """Index or disqualify each term, one result dict per term:
    {"keyword", "status", "post_count", "note"}.

    Indexed: its last-month posts (≤ KEYWORD_POST_CAP) are embedded into the
    post store. Disqualified: it had more than the cap and cannot be indexed.
    Already-known terms are skipped — the store is the memory; nothing is
    re-embedded on later rounds.
    """
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=state.WINDOW_DAYS)
    results: list[dict] = []
    for term in terms:
        known = index_db.get_keyword(term)
        if known:
            results.append({"keyword": term, "status": known["status"],
                            "post_count": known.get("post_count", 0),
                            "note": "already in the keyword store"})
            print(f"  {term}: already {known['status']}", file=sys.stderr, flush=True)
            continue

        posts = _collect_posts(term, state.KEYWORD_POST_CAP, cutoff)
        count = len(posts)
        vec = embed.embed([term])[0]

        if count > state.KEYWORD_POST_CAP:
            index_db.add_keyword(term, vec, provenance, status="disqualified",
                                 post_count=count)
            results.append({"keyword": term, "status": "disqualified",
                            "post_count": count,
                            "note": f"too common: {count} posts in the last "
                                    f"{state.WINDOW_DAYS} days"})
            print(f"  {term}: {count} posts in {state.WINDOW_DAYS}d -> "
                  "disqualified (over cap)", file=sys.stderr, flush=True)
            continue

        index_db.add_keyword(term, vec, provenance, status="indexed",
                             post_count=count,
                             last_indexed=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                        time.gmtime()))
        if posts:
            candidates = [c for c in (extract(v) for v in posts)
                          if c["text"].strip()]
            if candidates:
                print(f"  {term}: {count} posts in {state.WINDOW_DAYS}d, "
                      f"embedding {len(candidates)}...", file=sys.stderr,
                      flush=True)
                vecs = embed.embed([c["text"] for c in candidates])
                rows = [{
                    "uri": c["uri"], "handle": c.get("handle", ""),
                    "did": c.get("did", ""),
                    "displayName": c.get("displayName", ""),
                    "text": c["text"],
                    "embedding": v, "keyword": term,
                    "createdAt": c.get("createdAt", ""),
                    "replyTo": c.get("replyTo", ""),
                    "media": "|".join(c.get("media") or []),
                    "likeCount": c.get("likeCount", 0),
                    "replyCount": c.get("replyCount", 0),
                    "repostCount": c.get("repostCount", 0),
                    "fit": False, "grade": 0, "graded": False,
                    "why": "", "judged": False,
                } for c, v in zip(candidates, vecs)]
                index_db.add_posts(rows)
            else:
                print(f"  {term}: {count} posts, all empty text, indexed as "
                      "bare keyword", file=sys.stderr, flush=True)
        results.append({"keyword": term, "status": "indexed", "post_count": count})
    return results