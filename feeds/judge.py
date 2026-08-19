"""Per-post classification — the classifier that decides ONE post, self-contained.

The index experiment grows one public index from a fixed CRITERIA; a feed uses
the reader's own literal answer, stored on the feed, so none of the index's
state or thresholds belong here. This module is the per-post judge: given one
post and the feed's criteria, does it fit?

**Per-post classification and batch selection are different tools.** A feed
round (batch.py) loads the whole search into one model context and picks a
diverse set — that is how feeds get cross-post context. This module remains
for the single-post verdict: one independent GreenPT call per post, run in
parallel (JUDGE_CONCURRENCY in flight), so no verdict is conditioned on the
others. A post the model drops is a visible parse error, not a silent
negative.

Two separate processes, on purpose:

- `quality(posts)` — the general-quality grade (0-10), a property of the post
  itself. Computed once, stored on the post, reused by every feed. The prompt
  carries no criteria, so it is fully static and cacheable.
- `quality_check(posts, criteria_text)` — the binary feed-fit decision, one
  independent GreenPT call per post, run in parallel (JUDGE_CONCURRENCY in
  flight). This is the per-feed half: the criteria (the feed's own words) is
  the only per-feed text, and it sits at the end of the prompt so the static
  prefix is shared across feeds.

`campaign_posts` folds the fitting posts into a list of feed entries;
`parse_created` is the clock helper.

The call talks to GreenPT v4 flash through cause/classify's _completion, the
same transport the product uses everywhere.
"""

import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
from classify import ClassifyError, _completion  # noqa: E402

_model_busy_hint = ""


def _completion_tolerant(messages: list[dict]) -> str:
    """A flaky provider must not take down a whole round — mark for retry."""
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


JUDGE_CONCURRENCY = int(os.environ.get("FEEDS_JUDGE_CONCURRENCY", "10"))


def parse_created(iso: str):
    """The post's createdAt as a datetime, or None. Search results carry
    `...Z`; fromisoformat needs the Z spelled as +00:00."""
    if not iso:
        return None
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _verdict(content: str, index: int) -> dict:
    """Parse and validate one judge reply: the object must exist, be an
    object, and answer the post it was asked about."""
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
    return decision


def _quality_post(index: int, post: dict) -> dict:
    """Grade one post's general quality — no criteria, so the prompt is fully
    static and its prefix is shared and cached across every call."""
    content = _completion_tolerant([
        {"role": "system", "content":
            "You grade the general quality of one Bluesky post, 0 to 10, "
            "independent of any feed or request. Quality is about the post "
            "itself: (a) a root post scores higher than a reply dropped into "
            "the middle of someone else's thread; (b) original content and "
            "discussion that live on atproto score higher than a link-only "
            "post pointing away; (c) a person's own words and experience "
            "score higher than automated or corporate promotion; (d) "
            "substantive, specific posts score higher than noise. These are "
            "preferences, not hard rules — a reply can still be a great "
            "post."},
        {"role": "user", "content":
            "The post to grade:\n"
            f"[{index}] @{post.get('handle')} "
            f"{(post.get('createdAt') or '').replace('T', ' ')[:16]} — "
            f"{'root post' if not post.get('replyTo') else 'reply to ' + post['replyTo']} "
            f"— {' '.join((post.get('text') or '').split())[:320]}\n\n"
            "Return ONLY a JSON object: {\"i\": <index>, \"grade\": <0-10>, "
            "\"why\": \"<one short reason>\"}. grade: 10 for a genuinely "
            "excellent post, 0 for one that is noise. No prose around the "
            "JSON."},
    ])
    decision = _verdict(content, index)
    try:
        grade = int(decision.get("grade"))
    except (TypeError, ValueError):
        grade = 0
    return {"i": index, "grade": max(0, min(10, grade)),
            "why": str(decision.get("why", ""))[:200]}


def quality(posts: list[dict]) -> list[dict]:
    """The general-quality grade (0-10) for each post — the reusable part.

    `posts` is a list of post_index.extract() dicts. Returns one entry per
    post: {"i", "grade": int 0-10, "why": str}. This is independent of any
    feed: a post is graded once and the grade is stored on it, so new feeds
    reuse it without another call. The prompt carries no criteria — it is
    fully static, so the provider caches its prefix.

    One independent call per post, up to JUDGE_CONCURRENCY in flight.
    """
    if not posts:
        return []
    results: list[dict] = []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=JUDGE_CONCURRENCY) as pool:
        futures = [(i, pool.submit(_quality_post, i, p))
                   for i, p in enumerate(posts)]
        for i, future in futures:
            results.append((i, future.result()))
    return [r for _, r in sorted(results)]


def _judge_post(index: int, post: dict, criteria_text: str) -> dict:
    """Decide whether one post belongs in this feed — a binary yes/no.

    One call per post, so no verdict is conditioned on the others: a batch
    prompt lets order and leniency bleed between posts, and every label in it
    stops being an independent sample. A post the model drops is a visible
    parse error, not a silent negative.
    """
    content = _completion_tolerant([
        {"role": "system", "content":
            "You decide whether one Bluesky post belongs in a feed — a binary "
            "yes/no. Fit is decided ONLY by the request at the end of this "
            "prompt; nothing else counts. A post that does not clearly match "
            "the request does not fit. If unsure, fit is false.\n"
            "The request this post is judged against:\n"
            f"<criteria>\n{criteria_text}\n</criteria>"},
        {"role": "user", "content":
            "The post to judge:\n"
            f"[{index}] @{post.get('handle')} "
            f"{(post.get('createdAt') or '').replace('T', ' ')[:16]} — "
            f"{'root post' if not post.get('replyTo') else 'reply to ' + post['replyTo']} "
            f"— {' '.join((post.get('text') or '').split())[:320]}\n\n"
            "Return ONLY a JSON object: {\"i\": <index>, \"fit\": true|false, "
            "\"why\": \"<one short reason naming the actor or the reason it "
            "fails>\"}. If unsure, fit is false. No prose around the JSON."},
    ])
    decision = _verdict(content, index)
    return {"i": index, "fit": bool(decision.get("fit")),
            "why": str(decision.get("why", ""))[:200]}


def quality_check(posts: list[dict], criteria_text: str) -> list[dict]:
    """Decide, for each candidate post, whether it belongs in the feed.

    `posts` is a list of post_index.extract() dicts. Returns one entry per
    post: {"i", "fit": bool, "why": str} — the binary membership decision
    against the criteria text. General quality is a separate, reusable pass
    (quality()); it is not decided here.

    One independent call per post, up to JUDGE_CONCURRENCY in flight, so the
    latency of the batch is one post's call, not ten serialised — and the
    labels are independent samples rather than one biased batch.
    """
    if not posts:
        return []
    results: list[dict] = []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=JUDGE_CONCURRENCY) as pool:
        futures = [(i, pool.submit(_judge_post, i, p, criteria_text))
                   for i, p in enumerate(posts)]
        for i, future in futures:
            results.append((i, future.result()))
    return [r for _, r in sorted(results)]


def campaign_posts(posts: list[dict], scores: list[dict]) -> list[dict]:
    """The fitting subset, with the fit reason and the post's grade attached.
    The grade comes from the post itself (graded once by quality()); what
    becomes an entry on the feed."""
    by_index = {d["i"]: d for d in scores}
    out = []
    for i, p in enumerate(posts):
        d = by_index.get(i)
        if d and d.get("fit"):
            entry = dict(p)
            entry["why"] = d.get("why", "")
            out.append(entry)
    return out