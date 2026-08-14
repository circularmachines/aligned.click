#!/usr/bin/env python3
"""The evolutionary keyword exploration loop.

A keyword crawler that grows an index of grassroots environmental posts on
atproto. Each cycle takes an untried keyword and:

1. retrieves its latest posts on Bluesky;
2. quality-checks them against the index's main criteria (LLM judgment):
   how many fit?
3. if enough fit, the passing posts are indexed AND mined for new search
   terms, which join the pool as the next untried keywords.

Run a single cycle by hand, or leave it looping:

    python3 index/crawl.py --once                # one keyword, one cycle
    python3 index/crawl.py --candidates 3        # three keywords this cycle
    python3 index/crawl.py --interval 1800       # loop forever, 30 min apart

State lives in index/keywords.json (the keyword pool, with provenance) and
index/posts.json (the verified index, keyed by URI so nothing is double-
indexed). The criteria and thresholds are data in index/growth.py — the start
point is to iterate on the quality check, not on the plumbing.

Search runs as the crawler's own account. With INDEX_BLUESKY_HANDLE and
INDEX_BLUESKY_APP_PASSWORD set in .env it hits Bluesky directly (read-only
search, revocable app password); otherwise it falls back to the OAuth sidecar.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "tools"))

import growth  # noqa: E402
import apppass  # noqa: E402
from bsky import BskyError  # noqa: E402
from classify import ClassifyError  # noqa: E402
from post_index import extract  # noqa: E402


def search_latest(term: str, limit: int) -> list[dict]:
    """Bluesky search, newest first, only posts from the last WINDOW_DAYS.

    The window is applied on the post's own createdAt, client-side — the
    public search API gives no reliable date range. A slightly larger batch is
    pulled and dated posts falling outside the window are dropped, so a sparse
    keyword returns only what is genuinely fresh.

    A multiword keyword is searched as the literal phrase, not as loose words
    — the same quoting the tools use (see tools/search_posts.build_query) — so
    "repair cafe" matches that exact phrase rather than any post with "repair"
    and "cafe" anywhere.

    Two transports: the crawler's own app password (read-only search, no OAuth
    sidecar) when configured, or the OAuth sidecar otherwise.
    """
    import datetime

    from search_posts import build_query
    query = build_query([term])

    if apppass.configured():
        views = apppass.xrpc_get(
            "app.bsky.feed.searchPosts",
            {"q": query, "sort": "latest", "limit": max(limit * 6, 60)})["posts"]
    else:
        from bsky import get
        views = get("app.bsky.feed.searchPosts",
                    {"q": query, "sort": "latest", "limit": max(limit * 6, 60)})["posts"]
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=growth.WINDOW_DAYS)
    fresh: list[dict] = []
    for v in views:
        when = growth.parse_created(((v.get("record") or {}).get("createdAt") or ""))
        if when is None or when >= cutoff:
            fresh.append(v)
        if len(fresh) >= limit:
            break
    return fresh


def find_acting_did() -> str | None:
    os.environ.setdefault("ACTING_DID", "")
    if os.environ.get("ACTING_DID"):
        return os.environ["ACTING_DID"]
    # A by-hand run may set the account in .env, like the tools do.
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ACTING_DID="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    import urllib.request
    sidecar = os.environ.get("OAUTH_SIDECAR", "http://127.0.0.1:4098").rstrip("/")
    try:
        with urllib.request.urlopen(f"{sidecar}/oauth/sessions", timeout=10) as r:
            import json
            dids = json.loads(r.read()).get("dids", [])
        return dids[0] if dids else None
    except (OSError, urllib.error.HTTPError):
        return None


def _session_hint(err: str) -> bool:
    """Is this search failure a session/login problem rather than a search
    problem? Those are transient — fixable by logging in — so the pool must
    not burn pools of keywords on them."""
    return ("no longer usable" in err or "has not logged in" in err
            or "log in again" in err or "Refresh token" in err)


def login_notice() -> None:
    print(
        "\nSearch was refused because the crawler's account is not usable. "
        "Every keyword was left untouched for retry.\n"
        "  1) app password: set INDEX_BLUESKY_HANDLE and "
        "INDEX_BLUESKY_APP_PASSWORD in .env (read-only, revocable in "
        "Bluesky → App Passwords), or\n"
        "  2) OAuth: ./cause/start.sh then open http://127.0.0.1:8780 and "
        "log in with your Bluesky handle.\n",
        file=sys.stderr)


JUDGEMENTS_FILE = ROOT / "judgements.jsonl"
MAX_CLASSIFY_RETRIES = int(os.environ.get("INDEX_MAX_RETRIES", "3"))


def _append_judgements(keyword: str, tested: str, candidates: list[dict],
                       scores: list[dict]) -> None:
    """One JSON line per retrieved post: its text and the LLM verdict.

    The raw material for studying what the quality check is doing — every post
    the crawler ever sees, with why it did or did not make the index.
    """
    by_index = {d["i"]: d for d in scores}
    with JUDGEMENTS_FILE.open("a") as f:
        for i, p in enumerate(candidates):
            d = by_index.get(i, {})
            f.write(json.dumps({
                "keyword": keyword,
                "tested": tested,
                "uri": p.get("uri"),
                "handle": p.get("handle"),
                "createdAt": p.get("createdAt"),
                "text": p.get("text"),
                "fit": bool(d.get("fit")),
                "why": d.get("why", ""),
            }, ensure_ascii=False) + "\n")


def explore_keyword(kw: dict, posts: dict[str, dict], did: str,
                    existing: list[dict]) -> list[dict]:
    """The quality check + harvest for one keyword.

    Mutates the keyword record and the posts index; returns the freshly
    harvested keywords (already deduped against the pool) so the caller can
    add them flat, not nested. The keyword is the unit of failure: errors mark
    it 'error' instead of killing the cycle.
    """
    term = kw["keyword"]
    kw["tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    views = search_latest(term, growth.POSTS_PER_KEYWORD)
    kw["posts_seen"] = len(views)
    if not views:
        kw["status"] = "pass"
        kw["pass_rate"] = 0.0
        kw["note"] = f"no posts in the last {growth.WINDOW_DAYS} days"
        kw["stats"] = growth.keyword_stats([], [], [])
        return []

    candidates = [extract(v) for v in views]
    scores = growth.quality_check(candidates, growth.CRITERIA)
    _append_judgements(term, kw["tested"], candidates, scores)
    kw["stats"] = growth.keyword_stats(views, candidates, scores)
    fitting = [s for s in scores if s.get("fit")]
    kw["pass_rate"] = len(fitting) / len(scores) if scores else 0.0
    kw["posts_confirmed"] = len(fitting)

    # Whatever the outcome, the fitting posts are the index.
    for entry in growth.campaign_posts(candidates, scores):
        uri = entry["uri"]
        entry["confirmed_by"] = [term]
        if uri not in posts:
            posts[uri] = entry
        else:
            prev = posts[uri]
            # Older runs stored confirmed_by as a bare string; normalise to a
            # list so a second keyword confirming the same post can be added.
            if isinstance(prev.get("confirmed_by"), str):
                prev["confirmed_by"] = [prev["confirmed_by"]]
            prev.setdefault("confirmed_by", []).append(term)

    if kw["pass_rate"] >= growth.PASS_RATE:
        kw["status"] = "pass"
        return growth.new_from(
            existing, growth.harvest_keywords(
                [candidates[s["i"]] for s in fitting], term), term) if fitting else []
    kw["status"] = "fail"
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="run one cycle and exit")
    parser.add_argument("--candidates", type=int, default=1,
                        help="how many untried keywords one cycle tries")
    parser.add_argument("--interval", type=int, default=1800,
                        help="seconds between cycles (loop mode)")
    parser.add_argument("--force", action="store_true",
                        help="re-check keywords that already have a terminal status")
    args = parser.parse_args()

    did = None
    if not apppass.configured():
        did = find_acting_did()
        if not did:
            print("No search account: set INDEX_BLUESKY_HANDLE and "
                  "INDEX_BLUESKY_APP_PASSWORD in .env (an app password for "
                  "the crawler's own account), or log a DID into the OAuth "
                  "sidecar.", file=sys.stderr)
            sys.exit(1)
        os.environ["ACTING_DID"] = did

    # One run keeps going through the pool as it grows: the queue is
    # re-derived after every keyword, so words harvested mid-run are tried in
    # the same run rather than left for the next 30-minute cycle. `--candidates`
    # caps the total for the run; `--once` exits when the pool dries up.
    keywords = growth.load_keywords()
    posts = growth.load_posts()
    processed = 0
    hit_login_error = False
    tried_this_run = set()
    while True:
        # A keyword reverted to candidate by a classifier retry (below) is
        # excluded this run so it cannot loop; it comes back next run.
        queue = [k for k in keywords
                 if (k["status"] == "candidate" and k["keyword"] not in tried_this_run)
                 or (args.force and k["status"] in ("pass", "fail"))]
        if not queue:
            print("no untried keywords left. Love the weeds you have: "
                  f"{len(posts)} posts in the index.", file=sys.stderr)
            if args.once:
                return
            time.sleep(args.interval)
            continue

        kw = queue[0]
        print(f"[explore] trying keyword: {kw['keyword']!r}", file=sys.stderr)
        new_keywords: list[dict] = []
        try:
            new_keywords = explore_keyword(kw, posts, did, keywords)
        except BskyError as e:
            kw["note"] = f"search failed: {e}"
            if _session_hint(str(e)):
                # A login problem is not a keyword problem: leave the keyword a
                # candidate and let the whole run stop, or one stale session
                # quietly poisons the entire pool.
                kw["status"] = "candidate"
                hit_login_error = True
            else:
                kw["status"] = "error"
        except apppass.AuthError as e:
            kw["note"] = f"search account refused: {e}"
            kw["status"] = "candidate"
            hit_login_error = True
        except ClassifyError as e:
            # A non-JSON classifier answer is a transient wording hiccup, not
            # a verdict: retry the keyword rather than retiring it. Capped so
            # a genuinely broken keyword is eventually parked as error.
            kw["retries"] = kw.get("retries", 0) + 1
            kw["note"] = f"classifier failed (retry {kw['retries']}): {e}"
            if kw["retries"] >= MAX_CLASSIFY_RETRIES:
                kw["status"] = "error"
            else:
                kw["status"] = "candidate"
        except apppass.BskySearchError as e:
            kw["status"] = "error"
            kw["note"] = f"search failed: {e}"
        except Exception as e:  # noqa: BLE001 — a bad keyword must not end the pool
            kw["status"] = "error"
            kw["note"] = f"{type(e).__name__}: {e}"

        # New keywords join the pool now, so they are tried later in this run.
        keywords.extend(new_keywords)
        tried_this_run.add(kw["keyword"])
        stats = growth.load_stats()
        stats.append({
            "keyword": kw["keyword"],
            "found_by": kw.get("found_by"),
            "tested": kw.get("tested"),
            "status": kw["status"],
            "pass_rate": kw.get("pass_rate"),
            "new_keywords": [c["keyword"] for c in new_keywords],
            "stats": kw.get("stats", {}),
        })
        growth._write_stats(stats)
        # Write after each keyword so a crash keeps whatever was done.
        growth._write_keywords(keywords)
        growth._write_posts(posts)
        summary(kw, new_keywords)
        processed += 1

        if hit_login_error:
            login_notice()
            return
        if processed >= args.candidates:
            break

    print(f"[explore] run done: {len(keywords)} keywords in pool, "
          f"{len(posts)} posts in index.", file=sys.stderr)
    if args.once:
        return
    time.sleep(args.interval)


def summary(kw: dict, new_keywords: list[dict]) -> None:
    rate = kw.get("pass_rate")
    rate = f"{rate:.0%}" if rate is not None else "?"
    note = f"  ({kw['note']})" if kw.get("note") else ""
    extra = ""
    if kw["status"] == "pass" and new_keywords:
        extra = f"  -> new keywords: {', '.join(c['keyword'] for c in new_keywords[:5])}"
    elif kw["status"] == "fail":
        extra = "  (did not meet the criteria)"
    print(f"[explore]   {kw['status']:>7}  {kw['keyword']!r}  fit {rate} "
          f"({kw.get('posts_confirmed', 0)} of {kw.get('posts_seen', 0)}){extra}{note}",
          file=sys.stderr)


if __name__ == "__main__":
    main()