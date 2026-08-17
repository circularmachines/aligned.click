"""The feed builder's own judgment cargo, self-contained.

The index experiment grows one public index from a fixed CRITERIA; a feed judge
the reader's own literal answer, stored on the feed, so none of the index's
state or thresholds belong here. This module is the whole LLM cargo: the
quality check (does a post fit the criteria?), the harvest (new search terms
from posts that fit), and the small helpers the crawler needs around them.
Feeds import only this — not index/growth.py, not index/state.

The three calls (post judgment, harvest, seed-keywords) talk to GreenPT v4
flash through cause/classify's _completion, the same transport the index uses.
"""

import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
from classify import ClassifyError, _completion, _find_json_array  # noqa: E402

_model_busy_hint = ""


def _completion_tolerant(messages: list[dict]) -> str:
    """A flaky provider must not take down a whole crawl — mark for retry."""
    global _model_busy_hint
    try:
        return _completion(messages)
    except ClassifyError as e:
        _model_busy_hint = str(e)
        raise


def _find_json_object(text: str) -> str:
    """The model may wrap the object in a code fence or add a stray line; the
    object itself is the only part that matters."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ClassifyError(
            "the classifier did not return a JSON object. Try again."
        )
    return text[start:end + 1]


JUDGE_CONCURRENCY = int(os.environ.get("FEEDS_JUDGE_CONCURRENCY", "4"))


def parse_created(iso: str):
    """The post's createdAt as a datetime, or None. Search results carry
    `...Z`; fromisoformat needs the Z spelled as +00:00."""
    if not iso:
        return None
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _judge_post(index: int, post: dict, criteria: str) -> dict:
    """Judge one post against the criteria, in isolation.

    One call per post, so no verdict is conditioned on the others: a batch
    prompt lets order and leniency bleed between posts, and every label in it
    stops being an independent sample of the judge — the wrong raw material
    for a binary classifier trained on these judgements. A post the model
    drops is a visible parse error, not a silent negative.
    """
    content = _completion_tolerant([
        {"role": "system", "content":
            "You decide whether one Bluesky post belongs in a feed. Whether it "
            "belongs is the criteria below; apply it strictly and refuse when "
            "the post does not clearly fit.\n"
            f"<criteria>\n{criteria}\n</criteria>"},
        {"role": "user", "content":
            "The post to judge:\n"
            f"[{index}] @{post.get('handle')} "
            f"{(post.get('createdAt') or '').replace('T', ' ')[:16]} — "
            f"{' '.join((post.get('text') or '').split())[:320]}\n\n"
            "Return ONLY a JSON object: {\"i\": <index>, \"fit\": true|false, "
            "\"why\": \"<one short reason naming the grassroots actor or the "
            "reason it fails>\"}. If unsure, fit is false. No prose around "
            "the JSON."},
    ])
    try:
        decision = json.loads(_find_json_object(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"quality check JSON did not parse ({e})") from None
    if not isinstance(decision, dict):
        raise ClassifyError("quality check returned a non-object")
    try:
        got = int(decision.get("i"))
    except (TypeError, ValueError):
        got = -1
    if got != index:
        raise ClassifyError(
            f"quality check answered post {got}, asked for {index}")
    return {"i": index, "fit": bool(decision.get("fit")),
            "why": str(decision.get("why", ""))[:200]}


def quality_check(posts: list[dict], criteria: str) -> list[dict]:
    """Judge each candidate post against the criteria, in parallel.

    `posts` is a list of post_index.extract() dicts. Returns one entry per
    post: {"i", "fit": bool, "why": str}. The judge is GreenPT v4 flash.

    One independent call per post, up to JUDGE_CONCURRENCY in flight, so the
    latency of the batch is one post's call, not ten serialised — and the
    labels are independent samples rather than one biased batch.
    """
    if not posts:
        return []
    results: list[dict] = []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=JUDGE_CONCURRENCY) as pool:
        futures = [(i, pool.submit(_judge_post, i, p, criteria))
                   for i, p in enumerate(posts)]
        for i, future in futures:
            results.append((i, future.result()))
    return [r for _, r in sorted(results)]


def campaign_posts(posts: list[dict], scores: list[dict]) -> list[dict]:
    """The fitting subset, with the judge's why attached. What becomes an
    entry on the feed."""
    by_index = {d["i"]: d for d in scores}
    out = []
    for i, p in enumerate(posts):
        d = by_index.get(i)
        if d and d.get("fit"):
            entry = dict(p)
            entry["why"] = d.get("why", "")
            out.append(entry)
    return out


def harvest_keywords(posts: list[dict], seed: str, limit: int = 3) -> list[str]:
    """Mine posts that fit for NEW search terms.

    A seed keyword's passing posts are inspected and new 1-3 word terms that
    would retrieve more posts like them are returned. Nothing here edits the
    live pool; the caller decides what is genuinely new.
    """
    if not posts:
        return []
    lines = "\n".join(
        f"- {' '.join((p.get('text') or '').split())[:320]} (by @{p.get('handle')})"
        for p in posts)
    content = _completion_tolerant([
        {"role": "system", "content":
            "You discover search terms for a Bluesky feed. Given example posts "
            "that already fit the feed's criteria, you name terms (1-3 words "
            "each) that would retrieve more posts like them: the kind of "
            "activity, the kind of group, common event names.\n"
            "How a term is matched, exactly: a single word is searched as that "
            "word; a multi-word term is searched as the exact phrase in that "
            "order — it does NOT match posts that only contain some of those "
            "words. There is no OR-ing and no word-by-word matching. So a term "
            "like \"repair cafe\" retrieves posts containing the phrase "
            "\"repair cafe\", and a term like \"mending\" retrieves posts "
            "containing that word. Name phrases that genuinely occur together "
            "in that order; when in doubt, prefer a good single word.\n"
            "Skip anything that is just the seed keyword or an obvious "
            "duplicate of it. Skip brand names and specific places."},
        {"role": "user", "content":
            f"The seed keyword: {seed}\nExample fitting posts:\n" + lines +
            "\n\nReturn ONLY a JSON array of new search terms, at most "
            f"{limit}. No prose around the JSON."},
    ])
    try:
        terms = json.loads(_find_json_array(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"harvest JSON did not parse ({e})") from None
    if not isinstance(terms, list):
        raise ClassifyError("harvest returned an object, not an array")
    cleaned: list[str] = []
    for t in terms:
        if not isinstance(t, str):
            continue
        t = t.strip()
        if 1 < len(t) <= 40 and t.lower() not in cleaned:
            cleaned.append(t)
    return cleaned[:limit]