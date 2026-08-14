"""The evolutionary keyword loop, in its parts.

Goal: an index of grassroots environmental posts on atproto. It grows itself:

1. pick an untried keyword;
2. quality-check it — of the latest posts it retrieves, how many fit the
   index's criteria? (LLM judgment);
3. keywords that pass are *surfaced to harvest*: the posts that fit get mined
   for new search terms not yet in the database, which become the next
   untried keywords.

Everything here is the pure logic plus the two LLM calls (quality check and
harvest). The crawling loop lives in crawl.py. This is deliberately a starting
point — the hard part is the quality check, and the point is to iterate on it.

The main criteria and every threshold live as data here so they can drift
without code becoming archaeology.
"""

import datetime
import json
import os
import re
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
REPO = ROOT.parent

sys.path.insert(0, str(ROOT.parent / "cause"))
from classify import ClassifyError, _completion, _find_json_array  # noqa: E402

# --- the index's main criteria ----------------------------------------------

# What "grassroots environmental" means, for the quality check. This IS the
# product's definition of good, so it lives next to the loop that applies it.
CRITERIA = (
    "A post belongs in the index when a local, mostly volunteer group, "
    "person, or community is doing hands-on environmental work: repair "
    "cafes, fix-it nights, tool libraries, community gardens, seed swaps "
    "and seed libraries, river/ocean/village cleanups, community fridges "
    "and food rescue, bike kitchens, community energy, sharing and "
    "reuse, local restoration. The speaker or subject is the grassroots "
    "actor itself.\n"
    "It does NOT belong when the subject is: national campaigns, corporate "
    "greenwash, product promotion or ads, news headlines, pure politics, "
    "or academic/national NGO press releases. Merch and 'look at this "
    "gadget' do not belong.\n"
    "If you are unsure whether a post fits, it fits."
)

# How many of a keyword's latest posts must fit for the keyword to pass and be
# mined for new keywords. 0.5 ("at least half") is the starting threshold.
PASS_RATE = float(os.environ.get("INDEX_PASS_RATE", "0.2"))
POSTS_PER_KEYWORD = int(os.environ.get("INDEX_POSTS", "10"))

# The search window: only posts from this far back count. Applied on the post's
# own createdAt, client-side, because the public search API gives no reliable
# date range. A sparse keyword simply returns fewer than POSTS_PER_KEYWORD.
WINDOW_DAYS = int(os.environ.get("INDEX_WINDOW_DAYS", "30"))

# The seed keywords the index starts from, before it has harvested anything.
# `found_by` is their provenance: "seed" rather than a parent keyword. They
# live in index/seeds.txt (one per line) so restarting discovery is just
# deleting the runtime files — see seed_keywords().
SEEDS_FILE = ROOT / "seeds.txt"
DEFAULT_SEEDS = ["repair cafe", "fix it night", "tool library",
                "community garden", "seed swap", "river cleanup"]


def seed_keywords() -> list[str]:
    """The start keywords, from the one committed file index/seeds.txt.

    Edit that file to steer the search. Deleting index/keywords.json re-seeds
    the pool from here while the verified posts in index/posts.json survive.
    """
    if SEEDS_FILE.exists():
        words = [l.strip() for l in SEEDS_FILE.read_text().splitlines() if l.strip()]
        if words:
            return words
    return DEFAULT_SEEDS


KEYWORDS_FILE = ROOT / "keywords.json"
POSTS_FILE = ROOT / "posts.json"
STATS_FILE = ROOT / "stats.json"

_model_busy_hint = ""


def _completion_tolerant(messages: list[dict]) -> str:
    """Happier error for the crawl: a flaky provider or a wording hiccup must
    not take down a whole cycle, it must mark the keyword for retry."""
    global _model_busy_hint
    try:
        return _completion(messages)
    except ClassifyError as e:
        _model_busy_hint = str(e)
        raise


# --- state -------------------------------------------------------------------


def load_keywords() -> list[dict]:
    """The keyword database, seeded on first run. `status` is one of:
    candidate (untried), pass (fits the criteria), fail (does not), error
    (a run failed and it may be retried)."""
    if KEYWORDS_FILE.exists():
        try:
            keywords = json.loads(KEYWORDS_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            keywords = []
        return _dedup(keywords)
    seeds = [{"keyword": k, "found_by": "seed", "status": "candidate",
              "pass_rate": None, "tested": None, "posts_seen": 0,
              "posts_confirmed": 0} for k in seed_keywords()]
    _write_keywords(seeds)
    return seeds


def _dedup(keywords: list[dict]) -> list[dict]:
    """One entry per keyword, ever. A stale run that stored the same keyword
    twice (or nested under a parent) must not hand the loop a duplicate to
    re-check, so later entries are dropped, the terminal status wins, and the
    old nested `children` structure is flattened away (harvested words are
    already top-level)."""
    seen: dict[str, dict] = {}
    for k in keywords:
        norm = _norm(k.get("keyword", ""))
        if not norm:
            continue
        k.pop("children", None)
        prev = seen.get(norm)
        if prev is None:
            seen[norm] = k
            continue
        # Prefer the entry that has reached a terminal state.
        terminal = ("pass", "fail", "error")
        if k.get("status") in terminal and prev.get("status") not in terminal:
            seen[norm] = k
    return list(seen.values())


def _write_keywords(keywords: list[dict]) -> None:
    KEYWORDS_FILE.write_text(json.dumps(keywords, ensure_ascii=False, indent=2))


def load_posts() -> dict[str, dict]:
    """The index itself: verified posts, keyed by at:// URI so nothing is
    indexed twice. Each entry carries the criteria-evidence that got it in."""
    if POSTS_FILE.exists():
        try:
            return json.loads(POSTS_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _write_posts(posts: dict[str, dict]) -> None:
    POSTS_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2))


# --- keyword statistics ------------------------------------------------------
#
# One record per quality-check run, appended to stats.json — the file that
# shows how the pool is actually behaving, and the raw material for later
# tuning the criteria and thresholds.


def load_stats() -> list[dict]:
    if STATS_FILE.exists():
        try:
            return json.loads(STATS_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return []


def _write_stats(runs: list[dict]) -> None:
    STATS_FILE.write_text(json.dumps(runs, ensure_ascii=False, indent=2))


def parse_created(iso: str):
    """The post's createdAt as a datetime, or None. Search results carry
    `...Z`; fromisoformat needs the Z spelled as +00:00."""
    if not iso:
        return None
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def keyword_stats(views: list[dict], candidates: list[dict],
                  scores: list[dict]) -> dict:
    """What a keyword's check picked up, as numbers:
    how many posts, how many unique authors, media types, languages, likes.

    `candidates[i]` is the extract() of `views[i]`; `scores` is the quality
    check output. Both lists are parallel to views.
    """
    fit = {d["i"] for d in scores if d.get("fit")}
    n = len(candidates)
    confirmed_views = [v for i, v in enumerate(views) if i in fit]

    stats: dict = {"window_days": WINDOW_DAYS}

    stats["posts_seen"] = n
    stats["posts_confirmed"] = len(fit)
    stats["unique_authors"] = len({c.get("did") for c in candidates})
    stats["authors_confirmed"] = len({candidates[i].get("did") for i in fit})

    media: dict[str, int] = {}
    for c in candidates:
        buckets = set()
        for tag in (c.get("media") or []):
            if tag.startswith("images"):
                buckets.add("images")
            elif tag == "video":
                buckets.add("video")
            elif tag.startswith("link"):
                buckets.add("link")
            elif tag == "quote":
                buckets.add("quote")
        buckets = buckets or {"none"}
        for b in buckets:
            media[b] = media.get(b, 0) + 1
    stats["media"] = dict(sorted(media.items()))

    langs: dict[str, int] = {}
    for i, v in enumerate(views):
        for lang in (v.get("record") or {}).get("langs") or []:
            langs[lang] = langs.get(lang, 0) + 1
    stats["language"] = dict(sorted(langs.items(), key=lambda kv: -kv[1]))

    def _sum(key):
        return sum(c.get(key) or 0 for c in candidates)

    likes, reposts, replies = _sum("likeCount"), _sum("repostCount"), _sum("replyCount")
    confirmed_likes = sum((candidates[i].get("likeCount") or 0) for i in fit)
    stats["engagement"] = {
        "likes": likes, "reposts": reposts, "replies": replies,
        "avg_likes": round(likes / n, 1) if n else 0,
        "avg_reposts": round(reposts / n, 1) if n else 0,
        "confirmed_likes": confirmed_likes,
    }
    return stats


# --- the two LLM calls -------------------------------------------------------


def quality_check(posts: list[dict], criteria: str = CRITERIA) -> list[dict]:
    """Judge each candidate post against the criteria.

    `posts` is a list of post_index.extract() dicts. Returns one entry per
    post: {"i", "fit": bool, "why": str}. The judge is GreenPT v4 flash.
    """
    if not posts:
        return []
    lines = "\n".join(
        f"[{i}] @{p.get('handle')} {(p.get('createdAt') or '').replace('T', ' ')[:16]}"
        f" — {' '.join((p.get('text') or '').split())[:320]}"
        for i, p in enumerate(posts))
    content = _completion_tolerant([
        {"role": "system", "content":
            "You decide whether a Bluesky post belongs in a public index of "
            "grassroots environmental work. The index's definition of "
            "belonging is the criteria below; apply it strictly and refuse "
            "when the post does not clearly fit.\n"
            f"<criteria>\n{criteria}\n</criteria>"},
        {"role": "user", "content":
            "The posts to judge:\n" + lines + "\n\nReturn ONLY a JSON array, "
            "one object per post: {\"i\": <index>, \"fit\": true|false, "
            "\"why\": \"<one short reason naming the grassroots actor or the "
            "reason it fails>\"}. If unsure, fit is false. No prose around "
            "the JSON."},
    ])
    try:
        decisions = json.loads(_find_json_array(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"quality check JSON did not parse ({e})") from None
    if not isinstance(decisions, list):
        raise ClassifyError("quality check returned an object, not an array")
    result: list[dict] = []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        try:
            idx = int(d.get("i"))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(posts):
            result.append({"i": idx, "fit": bool(d.get("fit")),
                           "why": str(d.get("why", ""))[:200]})
    return result


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
            "You discover search terms for a Bluesky index of grassroots "
            "environmental work. Given example posts that already fit the "
            "index, you name terms (1-3 words each) that would retrieve more "
            "posts like them: the kind of activity, the kind of group, common "
            "event names. Skip anything that is just the seed keyword or an "
            "obvious duplicate of it. Skip brand names and specific places."},
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


def _norm(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def campaign_posts(posts: list[dict], scores: list[dict]) -> list[dict]:
    """The verified subset: posts whose quality check said fit, with the
    evidence attached. What becomes an entry in the index."""
    by_index = {d["i"]: d for d in scores}
    out = []
    for i, p in enumerate(posts):
        d = by_index.get(i)
        if d and d.get("fit"):
            entry = dict(p)
            entry["confirmed_by"] = None  # set by the caller
            entry["why"] = d.get("why", "")
            out.append(entry)
    return out


def new_from(existing: list[dict], terms: list[str], parent: str) -> list[dict]:
    """Terms that are genuinely new: not already a keyword, not the parent."""
    known = {_norm(kw["keyword"]) for kw in existing}
    known.add(_norm(parent))
    fresh = []
    for t in terms:
        if _norm(t) in known:
            continue
        known.add(_norm(t))
        fresh.append({"keyword": t, "found_by": parent, "status": "candidate",
                      "pass_rate": None, "tested": None, "posts_seen": 0,
                      "posts_confirmed": 0, "children": []})
    return fresh
