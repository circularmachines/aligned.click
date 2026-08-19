#!/usr/bin/env python3
"""Batch selection — the round's one-shot selector for one feed.

Feeds got too random when each post was judged in isolation, because a
per-post classifier has no cross-post context: it cannot see that five
near-copies in a row are five near-copies, or that this round is all one
repair café and nothing like the robotics workshop the reader kept last week.
So a round is one search and ONE call:

1. **Search the pool** — up to KEYWORDS_PER_FEED keywords, at most
   POSTS_PER_KEYWORD fresh posts each, everything inside WINDOW_DAYS;
2. **Load the whole batch into one context** — every candidate post tagged
   with the keyword that retrieved it, together with the reader's curation
   from earlier rounds (included posts as positive examples, discarded as
   negative);
3. **One shot in** — the model returns up to SUGGEST_COUNT posts that belong
   but are DIFFERENT from each other (different authors and angles, not one
   thread five times); a refined per-post-classifier-prompt (the reader's
   criteria sharpened by what this round proved); and the seeder pool to
   search next round.

The reader includes or discards each suggestion; the next round carries that
history forward. The feed is grown in rounds, not by a background crawl:
`run_batch()` is where "which post belongs here" is decided, with the
cross-post context the old loop lacked.

    python3 feeds/batch.py <id>       # run one round for a feed

The call talks to GreenPT v4 flash through cause/classify's _completion, the
same transport the product uses everywhere. Search uses the index account
(.env), the same way the old crawler did.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT.parent / "index"))
sys.path.insert(0, str(ROOT.parent / "cause"))
sys.path.insert(0, str(ROOT))

import state  # noqa: E402
import apppass  # noqa: E402
import judge  # noqa: E402
from bsky import get  # noqa: E402
from classify import ClassifyError  # noqa: E402
from post_index import extract  # noqa: E402
from search_posts import build_query  # noqa: E402


# --- retrieving the round's candidates ---------------------------------------


def search_posts(keyword: str) -> list[dict]:
    """The keyword's fresh posts in the window, capped at POSTS_PER_KEYWORD.

    One page of search results is capped at 100 posts; we take the newest
    POSTS_PER_KEYWORD that are still inside WINDOW_DAYS by the post's own
    createdAt. This is a round's search: enough to see the keyword's current
    supply, never the whole history.
    """
    query = build_query([keyword])
    if apppass.configured():
        views = apppass.xrpc_get("app.bsky.feed.searchPosts",
                                 {"q": query, "sort": "latest", "limit": 100})["posts"]
    else:
        views = get("app.bsky.feed.searchPosts",
                    {"q": query, "sort": "latest", "limit": 100})["posts"]
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=state.WINDOW_DAYS)
    fresh: list[dict] = []
    for v in views:
        when = judge.parse_created(((v.get("record") or {}).get("createdAt") or ""))
        if when is not None and when >= cutoff:
            fresh.append(extract(v))
        if len(fresh) >= state.POSTS_PER_KEYWORD:
            break
    return fresh


def collect(feed: dict) -> list[dict]:
    """One round's candidate batch.

    Searches the feed's pool, dedupes by uri, tags each post with the keyword
    that found it, and drops anything already offered to the reader (seen,
    included, discarded). Capped at MAX_BATCH, so a giant pool cannot blow up
    the context. BskyError propagates to the caller.
    """
    already = set(feed.get("seen") or []) | set(feed.get("included") or {}) \
        | set(feed.get("discarded") or {})
    known: set[str] = set()
    batch: list[dict] = []
    for keyword in feed.get("keywords") or []:
        for post in search_posts(keyword):
            if post["uri"] in already or post["uri"] in known:
                continue
            known.add(post["uri"])
            item = dict(post)
            item["found_by"] = keyword
            batch.append(item)
            if len(batch) >= state.MAX_BATCH:
                return batch
    return batch


# --- one-shot selection ------------------------------------------------------


def _history(feed: dict) -> str:
    """The reader's curation as compact example lines: kept posts are the
    positive examples, discarded are the negative ones."""
    def _line(uri: str, entry: dict) -> str:
        date = (entry.get("createdAt") or "").replace("T", " ")[:16] or "?"
        text = " ".join((entry.get("text") or "").split())[:200]
        return f"  @{entry.get('handle')}  {date} — {text}"
    parts = []
    kept = list((feed.get("included") or {}).values())[-6:]
    if kept:
        parts.append("The reader KEPT these (they belong; a good pick looks "
                     "like this):\n" + "\n".join(_line(e.get("uri", ""), e)
                                                 for e in kept))
    dropped = list((feed.get("discarded") or {}).values())[-6:]
    if dropped:
        parts.append("The reader DISCARDED these (they do not belong):\n"
                     + "\n".join(_line(e.get("uri", ""), e) for e in dropped))
    return "\n".join(parts)


def _user(batch: list[dict]) -> str:
    """Every candidate, grouped by the keyword that retrieved it. The model
    sees WHICH search found WHICH post, along with every other keyword of the
    round, so it can judge the batch as one search."""
    by_keyword: dict[str, list[str]] = {}
    for i, post in enumerate(batch):
        by_keyword.setdefault(post.get("found_by", ""), []).append(
            f"[{i}] @{post.get('handle')}  "
            f"{(post.get('createdAt') or '').replace('T', ' ')[:16]} — "
            f"{' '.join((post.get('text') or '').split())[:300]}")
    groups = "\n".join(
        f'keyword "{kw}" →\n' + "\n".join(lines)
        for kw, lines in by_keyword.items())
    return (
        "The round searched these keywords, and below each is what that "
        "search returned (posts may appear under several keywords;\n"
        "indices are from the whole batch, not per keyword):\n\n"
        + groups + "\n\n"
        f"Pick up to {state.SUGGEST_COUNT} posts that belong in the feed but "
        "are DIFFERENT from each other — different authors and different "
        "angles, never one thread of replies twice, never five posts that are "
        "effectively the same thing. For each pick, one short reason naming "
        "what makes it fit and how it differs.\n"
        "Then write the refined criteria: a one-line version of the reader's "
        "request that this round showed is accurate — what belongs on the "
        "feed, in the reader's own words, sharpened by the posts kept and "
        "discarded above.\n"
        "Then name the next seeder pool: search terms that would find MORE "
        "posts like the ones you picked (1-3 words each, lowercase, no "
        "quotes).\n"
        "Return ONLY JSON: {\"picks\": [{\"i\": <index>, \"why\": "
        "\"<reason>\"}], \"criteria\": \"<refined one-line prompt>\", "
        "\"keywords\": [\"<seed term>\", ...]}. No prose around the JSON."
    )


def one_shot(feed: dict, batch: list[dict]) -> dict:
    """The single call that is a round: the whole search plus the reader's
    history in one context, returning picks, the refined criteria, and the
    next seeder pool."""
    content = judge._completion_tolerant(messages(feed, batch))
    try:
        parsed = json.loads(judge._find_json_object(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"the selector's JSON did not parse ({e})") from None
    if not isinstance(parsed, dict):
        raise ClassifyError("the selector returned a non-object")
    return parsed


def messages(feed: dict, batch: list[dict]) -> list[dict]:
    """The exact LLM messages a round sends: the criteria + the reader's
    curation history as the system prompt, every search result grouped by
    keyword as the user prompt."""
    history = _history(feed)
    criteria = feed.get("criteria") or feed["text"]
    system = (
        "You curate one Bluesky feed. The reader told you what they want "
        "to see; that request below is the criteria, and this round's "
        "search is one batch you judge WITH the cross-post context a "
        "single-post judge never has.\n"
        "What you return: a small set of posts that belong in the feed "
        "BUT are different from each other; the criteria sharpened by "
        "what this round proved; and the seeder terms the next round "
        "should search. The picks must not repeat what the reader already "
        "kept, and must not repeat each other.\n"
        f"<criteria>\n{criteria}\n</criteria>\n"
        + (history or "")
    )
    user = (_user(batch) if batch
            else "The pool is empty right now — nothing fresh came back. "
                 "Return JSON with \"picks\": [], \"criteria\": \"\", "
                 "\"keywords\": [<the next terms to search>].")
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def _parse_picks(parsed: dict, batch: list[dict]) -> list[dict]:
    """The model's picks, validated against the real batch. Bad indices are
    dropped rather than failing the round."""
    picks: list[dict] = []
    raw = parsed.get("picks")
    if not isinstance(raw, list):
        return picks
    for p in raw[:state.SUGGEST_COUNT]:
        if not isinstance(p, dict):
            continue
        try:
            idx = int(p.get("i"))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(batch):
            entry = dict(batch[idx])
            entry["why"] = str(p.get("why", ""))[:220]
            picks.append(entry)
    return picks


# --- the round ---------------------------------------------------------------


def run_batch(feed_id: str, feeds: dict | None = None) -> dict:
    """Run one selection round for a feed and store its result on the record.

    Returns the feed after the round. `feeds` is the caller's loaded state
    (so web.py and the CLI share one write); when omitted it is loaded here.
    """
    feeds = feeds if feeds is not None else state.load_feeds()
    feed = feeds.get(feed_id)
    if feed is None:
        raise ValueError(f"no feed with id {feed_id}.")
    batch = collect(feed)
    parsed = one_shot(feed, batch)
    picks = _parse_picks(parsed, batch)

    pick_uris = {p["uri"] for p in picks}
    feed["suggested"] = picks
    feed["seen"] = list(set(feed.get("seen") or []) | pick_uris)

    criteria = str(parsed.get("criteria") or "").strip()
    if criteria:
        feed["criteria"] = criteria
    terms = parsed.get("keywords")
    if isinstance(terms, list):
        feed["keywords"] = state.pool(feed.get("keywords") or [],
                                      [str(t) for t in terms if isinstance(t, str)])
    feed["rounds"] = feed.get("rounds", 0) + 1
    feed["note"] = None
    state.save_feeds(feeds)
    return feed


# --- the continuous feed -----------------------------------------------------


def populate(feed_id: str, feeds: dict | None = None) -> dict:
    """The continuous generator: per-post judge the pool under the refined
    criteria and keep the fittings on the feed.

    A round's one-shot produced two outputs — the refined criteria (the
    per-post classifier's prompt) and the seeder pool — and this is where they
    are actually used. For every keyword still in the window, every fresh post
    is judged one by one (judge.quality_check, parallel), and everything that
    fits is kept on `feed["posts"]`: a feed grown by its own standard, the
    thing the reader reviews. This is the cadence that runs continuously; a
    round only happens when the reader asks to refocus.

    Nothing judged here influences the round's suggestions: `posts` is the
    feed, `suggested` is the next batch waiting to be curated. Posts the
    reader already discarded are never re-added.
    """
    feeds = feeds if feeds is not None else state.load_feeds()
    feed = feeds.get(feed_id)
    if feed is None:
        raise ValueError(f"no feed with id {feed_id}.")
    criteria = feed.get("criteria") or feed["text"]
    posts = feed.setdefault("posts", {})
    discarded = set(feed.get("discarded") or {})

    for keyword in feed.get("keywords") or []:
        fresh = [p for p in search_posts(keyword)
                 if p["uri"] not in posts and p["uri"] not in discarded]
        if not fresh:
            continue
        scores = judge.quality_check(fresh, criteria)
        for entry in judge.campaign_posts(fresh, scores):
            entry["found_by"] = keyword
            posts[entry["uri"]] = entry

    feed["note"] = None
    state.save_feeds(feeds)
    return feed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("id", nargs="?", default="",
                        help="the feed's id (or its unique prefix)")
    parser.add_argument("--new", default="",
                        help="create a feed from this request, then run its round")
    parser.add_argument("--dry-run", action="store_true",
                        help="search and print the exact LLM messages, no call")
    parser.add_argument("--populate", action="store_true",
                        help="then run the continuous per-post generator against "
                        "the stored criteria and pool")
    args = parser.parse_args(argv)

    feeds = state.load_feeds()

    if args.new:
        import harvest  # imported here: seeding is a separate, one-time step
        text = args.new.strip()
        if not text:
            print("the request is empty — say what kind of posts you want to "
                  "see more of.", file=sys.stderr)
            sys.exit(1)
        feed = state.new_feed(text)
        seeds = harvest.seed_keywords(text)
        feed["keywords"] = state.pool([], seeds)
        feeds[feed["id"]] = feed
        state.save_feeds(feeds)
        print(f"created feed {feed['id']}", file=sys.stderr)
        print(f"  planted {len(seeds)} keyword(s): {', '.join(seeds)}\n",
              file=sys.stderr)
        feed_id = feed["id"]
    else:
        feed_id = next((f for f in feeds
                        if f == args.id or f.startswith(args.id)), None)
        if not feed_id:
            print(f"no feed with id {args.id}.", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        try:
            feed = feeds[feed_id]
            batch = collect(feed)
        except (apppass.AuthError,
                Exception) as e:  # noqa: BLE001 — a verdict, not a traceback
            print(f"search failed: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"\"{feed['text']}\" — round {feed.get('rounds', 0) + 1}, "
              f"{len(batch)} candidate(s) from the search:\n", file=sys.stderr)
        for i, p in enumerate(batch):
            print(f"  [{i}] @{p.get('handle')}  {p.get('found_by')!r}  "
                  f"{' '.join((p.get('text') or '').split())[:160]}")
        for m in messages(feed, batch):
            print(f"\n===== {m['role']} =====\n{m['content']}")
        return

    try:
        feed = run_batch(feed_id, feeds)
        if args.populate:
            populate(feed_id, feeds)
    except (ValueError, ClassifyError,
            apppass.AuthError) as e:
        print(f"selection failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\"{feed['text']}\" — round {feed.get('rounds', 0)}, "
          f"{len(feed.get('posts') or {})} post(s) on the feed, "
          f"{len(feed.get('suggested') or [])} suggested:")
    if feed.get("criteria"):
        print(f"  criteria: {feed['criteria'][:200]}")
    for i, p in enumerate(feed.get("suggested") or [], 1):
        print(f"  {i}. @{p.get('handle')}  {p.get('found_by')!r}  {p['uri']}")
        print(f"     {' '.join((p.get('text') or '').split())[:200]}")
        if p.get("why"):
            print(f"     why: {p['why']}")
    print(f"  next seeder pool: {', '.join(feed.get('keywords') or [])}")


if __name__ == "__main__":
    main()