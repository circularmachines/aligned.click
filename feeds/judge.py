"""Post classification — the crawler's continuous process, self-contained.

The index experiment grows one public index from a fixed CRITERIA; a feed uses
the reader's own literal answer, stored on the feed, so none of the index's
state or thresholds belong here. This module is the whole LLM cargo of
*judging*: the quality check (does a post fit the criteria?) and the steering
that picks which candidate keyword's supply to judge next. Feeds import only
this — not index/growth.py, not index/state.

**Post judgement and keyword harvesting are separate processes.** Judging runs
continuously in crawl.py: it decides which posts fit and loads them onto the
feed, and never invents search terms. Keyword harvesting — generating the
search terms themselves — happens only once, when the feed is created, in
harvest.py (request.py calls harvest.seed_keywords). The crawler works the
pool it was given; it does not grow it.

The judging call is one independent GreenPT call per post, run in parallel
(JUDGE_CONCURRENCY in flight), so no verdict is conditioned on the others: a
batch prompt lets order and leniency bleed between posts, and every label
stops being an independent sample — the wrong raw material for a binary
classifier trained on these judgements. A post the model drops is a visible
parse error, not a silent negative.

`criteria(feed)` builds the judgement standard from the reader's own words;
`quality_check` is the per-post judge; `campaign_posts` folds fitting posts
into the feed; `parse_created` is the crawler's clock helper. The predictive
steering lives here too — it decides the *next thing to judge*, which is
judging's business, not harvesting's.

The call talks to GreenPT v4 flash through cause/classify's _completion, the
same transport the index uses.
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


def criteria(feed: dict) -> str:
    """The quality check's criteria for a feed: the literal answer, verbatim.

    This is the whole simplification. A feed request is not decoded into
    anything — the reader's words *are* the standard of fit. The final line
    refuses generously, so pass rates are real fits, not "probably similar
    enough".
    """
    return (
        "A post belongs in the feed when it matches, in the reader's own "
        "words, what they asked to see. The request:\n"
        f"{feed['text']}\n"
        "The subject or speaker is the kind of thing the request names. It "
        "does NOT belong when it is only vaguely related, an ad, news, or "
        "unrelated happenings. If you are unsure whether a post fits, it does "
        "not fit."
    )


def _judge_post(index: int, post: dict, criteria_text: str) -> dict:
    """Judge one post against the criteria, in isolation.

    One call per post, so no verdict is conditioned on the others: a batch
    prompt lets order and leniency bleed between posts, and every label in it
    stops being an independent sample — the wrong raw material for a binary
    classifier trained on these judgements. A post the model drops is a
    visible parse error, not a silent negative.
    """
    content = _completion_tolerant([
        {"role": "system", "content":
            "You decide whether one Bluesky post belongs in a feed. Whether it "
            "belongs is the criteria below; apply it strictly and refuse when "
            "the post does not clearly fit.\n"
            f"<criteria>\n{criteria_text}\n</criteria>"},
        {"role": "user", "content":
            "The post to judge:\n"
            f"[{index}] @{post.get('handle')} "
            f"{(post.get('createdAt') or '').replace('T', ' ')[:16]} — "
            f"{' '.join((post.get('text') or '').split())[:320]}\n\n"
            "Return ONLY a JSON object: {\"i\": <index>, \"fit\": true|false, "
            "\"why\": \"<one short reason naming the actor or the reason it "
            "fails>\"}. If unsure, fit is false. No prose around the JSON."},
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


def quality_check(posts: list[dict], criteria_text: str) -> list[dict]:
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
        futures = [(i, pool.submit(_judge_post, i, p, criteria_text))
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


# --- steering: the feedback loop drives which keyword to judge next -----------
#
# The crawl loop feeds the model the keyword ledger (pass rate + volume for
# every tried term) plus sampled verdicts, so it can prefer abundant directions
# and drop words the evidence says are noise. Steering only *picks* among the
# existing candidates — it never invents search terms. New terms come from
# harvest.py, at feed creation, on purpose.


def _history(feed: dict) -> str:
    """The keyword ledger as the steering model reads it: for each tried
    keyword, its pass rate, its volume (how often such posts occur in the
    window), and up to three of the newest verdicts sampled from it."""
    lines: list[str] = []
    for kw in feed.get("keywords") or []:
        rate = kw.get("pass_rate")
        rate_s = f"{rate:.0%}" if rate is not None else "untried"
        volume = kw.get("volume") or 0
        seen = kw.get("posts_seen") or 0
        confirmed = kw.get("posts_confirmed") or 0
        lines.append(
            f"- {kw.get('keyword')!r}: {kw.get('status', 'candidate')}, "
            f"fit {rate_s} ({confirmed}/{seen}), volume {volume}")
        for w in (kw.get("whys") or [])[-3:]:
            lines.append(f"    why: {w.get('why', '')[:120]}")
    return "\n".join(lines) if lines else "(nothing tested yet)"


def steer(feed: dict, candidates: list[dict], tried: set[str]) -> dict | None:
    """Decide which candidate to judge next, from the ledger.

    `candidates` is the untried pool; `tried` lets the model know which it
    already attempted. Returns a decision the caller obeys:
    {"action": "try"|"stop", "pick": <term>, "reason": <str>}, or None when
    the model's answer is unusable (the caller falls back to the oldest).
    """
    criteria_text = criteria(feed)
    goal = feed.get("goal") or 20
    have = len(feed.get("posts") or {})
    candidate_lines = "\n".join(f"- {kw['keyword']}" for kw in candidates)
    tried_s = ", ".join(sorted(tried)) or "(none yet)"
    content = _completion_tolerant([
        {"role": "system", "content":
            "You steer a Bluesky feed builder. The feed's criteria is the "
            "reader's own words; posts are judged against it and either fit "
            "the feed or not. Below you are given the keyword ledger from the "
            "crawl so far — for every term tried, the share of posts that fit "
            "(pass rate) and the volume of fresh posts that term finds in the "
            "window (how often such posts occur). You pick the next candidate "
            "to judge to reach the goal with the least wasted judging."},
        {"role": "user", "content":
            f"The reader asked to see:\n{criteria_text}\n\n"
            f"Goal: {goal} fitting posts on the feed; {have} so far.\n\n"
            f"Keyword ledger (term: status, fit rate (confirmed/seen), volume "
            f"+ sampled verdict reasons):\n{_history(feed)}\n\n"
            f"Untried candidates to pick from:\n{candidate_lines}\n\n"
            f"Already tried this run:{tried_s}\n\n"
            "Choose an action:\n"
            "  try: pick the single best candidate to judge next. Prefer high "
            "volume and high expected fit; avoid words whose sibling forms "
            "already failed.\n"
            "  stop: the remaining candidates look unpromising and further "
            "judging would waste the API budget.\n"
            "Return ONLY a JSON object: {\"action\": \"try\"|\"stop\", "
            "\"pick\": \"<one candidate term, or \\\"\\\" if not try>\", "
            "\"reason\": \"<one short sentence>\"}. No prose around it."},
    ])
    try:
        d = json.loads(_find_json_object(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"steer JSON did not parse ({e})") from None
    if not isinstance(d, dict):
        raise ClassifyError("steer returned a non-object")
    action = str(d.get("action", "")).strip().lower()
    if action == "try":
        return {"action": "try", "pick": str(d.get("pick", "")).strip(),
                "reason": str(d.get("reason", ""))[:200]}
    if action == "stop":
        return {"action": "stop", "pick": "",
                "reason": str(d.get("reason", ""))[:200]}
    return None
