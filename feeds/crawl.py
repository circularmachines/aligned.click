#!/usr/bin/env python3
"""The feed builder's assembly loop: for each feed, work its keyword pool
toward the goal (see state.FEEDS_GOAL).

One feed at a time, the same crank the index runs — search a keyword, judge
the posts against *this feed's* criteria (the literal answer), keep the posts
that fit. The judgment cargo is the feed's own, in judge.py; the index is not
imported.

**Post judgement and keyword harvesting are separate processes.** Judging is
the crawler's only job: it decides which posts fit and loads them onto the
feed, and never invents search terms. Harvesting — generating the search
terms in the first place — happens exactly once, when the feed is created, in
harvest.py (request.py calls seed_keywords). The crawler works the pool it
was given; it does not grow it.

Two judging phases, decided per cycle:

1. **Mine** — if an approved keyword (passed the pass-rate) still has fresh
   supply it has not judged, judge its next batch. This is how one good
   keyword fills the feed: the first trial proves it, then the loop keeps
   coming back to it instead of always drifting to a new word. Mining does
   not re-harvest — the keyword is already proven.
2. **Explore** — else, with no mineable keywords left, steering picks the next
   candidate to judge. When the candidate pool is empty, the loop has nothing
   left and gives up — new keywords are planted only when the feed is created.

The loop stops early when the goal is reached (status: ready), and gives up —
keeping whatever fit so far — when the pool is exhausted or the cycle cap is
hit (status: stalled).

    python3 feeds/crawl.py --once                # one cycle across feeds, exit
    python3 feeds/crawl.py --candidates 3        # three cycles this run, exit
    python3 feeds/crawl.py --goal                # assemble every feed to its goal
    python3 feeds/crawl.py --interval 1800       # loop forever, 30 min apart

State lives in feeds/feeds.json, one record per feed as described in state.py.
"""
import argparse
import sys
import time
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT.parent / "index"))
sys.path.insert(0, str(ROOT.parent / "cause"))

import state  # noqa: E402
import apppass  # noqa: E402
from bsky import BskyError  # noqa: E402
from classify import ClassifyError  # noqa: E402
from post_index import extract  # noqa: E402
from search_posts import build_query  # noqa: E402
import judge  # noqa: E402


def search_volume(term: str) -> list[dict]:
    """The keyword's full fresh supply in the window, uncapped by judging.

    One page of search results is capped at 100 posts; a volume probe pulls a
    wide window and counts how many are still inside it. This is what tells
    the steering model whether a topic is abundant (38 fresh posts) or sparse
    (2). Returns the fresh views themselves — the caller judges a slice and
    parks the rest for later mining.
    """
    import datetime

    query = build_query([term])
    if apppass.configured():
        views = apppass.xrpc_get("app.bsky.feed.searchPosts",
                                 {"q": query, "sort": "latest", "limit": 100})["posts"]
    else:
        from bsky import get
        views = get("app.bsky.feed.searchPosts",
                    {"q": query, "sort": "latest", "limit": 100})["posts"]
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=state.WINDOW_DAYS)
    fresh: list[dict] = []
    for v in views:
        when = judge.parse_created(((v.get("record") or {}).get("createdAt") or ""))
        if when is not None and when >= cutoff:
            fresh.append(v)
    return fresh


def _judge(feed: dict, kw: dict, views: list[dict], limit: int) -> bool:
    """Judge up to `limit` views against the feed's criteria: run the quality
    check, fold the fitting posts into the feed, update the keyword's stats.
    This is the ONLY place posts are ever judged. Returns True when more was
    judged (even if nothing fit)."""
    if not views:
        return False
    candidates = [extract(v) for v in views]
    scores = judge.quality_check(candidates, judge.criteria(feed))
    confirmed = sum(1 for s in scores if s.get("fit"))
    kw["posts_seen"] = kw.get("posts_seen", 0) + len(scores)
    kw["posts_confirmed"] = kw.get("posts_confirmed", 0) + confirmed
    kw["pass_rate"] = (kw["posts_confirmed"] / kw["posts_seen"]
                       if kw["posts_seen"] else 0.0)
    kw["whys"] = [{"fit": bool(s.get("fit")), "why": s.get("why", "")}
                  for s in scores][-10:]
    for entry in judge.campaign_posts(candidates, scores):
        feed["posts"][entry["uri"]] = entry
    return True


def try_keyword(feed: dict, kw: dict) -> bool:
    """First trial of a candidate keyword: probe its volume, judge one batch.
    Post judgement only. Returns True when the keyword passes. Nothing here
    generates new terms — the pool was planted at feed creation (harvest.py).
    """
    kw["tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    kw.pop("drained", None)
    views = search_volume(kw["keyword"])   # BskyError propagates to caller
    kw["volume"] = len(views)
    if not views:
        kw["note"] = "no fresh posts in the window"
        return False
    _judge(feed, kw, views[:state.POSTS_PER_KEYWORD], state.POSTS_PER_KEYWORD)
    if (kw.get("pass_rate") or 0.0) < state.PASS_RATE:
        kw["status"] = "fail"
        return False
    kw["status"] = "pass"
    return True


def mine_keyword(feed: dict, kw: dict) -> bool:
    """Mine the next MINE_BATCH posts of an approved keyword, deeper into the
    window than the first page reached. Post judgement only — the keyword is
    already proven; its job now is just to feed the feed. Returns True when
    more was judged.
    """
    kw["tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    views = search_volume(kw["keyword"])   # BskyError propagates to caller
    kw["volume"] = max(kw.get("volume", 0), len(views))
    if not views:
        kw["drained"] = True
        kw["note"] = "supply exhausted inside the window"
        return False
    seen = set(kw.get("seen") or [])
    fresh = [v for v in views
             if extract(v)["uri"] not in feed["posts"]
             and extract(v)["uri"] not in seen]
    if not fresh:
        kw["drained"] = True
        kw["note"] = "no unjudged fresh posts left in the window"
        return False
    batch = fresh[:state.MINE_BATCH]
    _judge(feed, kw, batch, state.MINE_BATCH)
    kw["seen"] = list(seen | {extract(v)["uri"] for v in batch})
    if (kw.get("pass_rate") or 0.0) < state.PASS_RATE:
        kw["status"] = "fail"   # one deep batch of filings, no more gold
    return True


def _best_mineable(feed: dict) -> dict | None:
    """The approved keyword most worth mining next: highest pass rate, not yet
    drained, with supply still in the window. Cheap and noisy; good enough to
    pick a mine target."""
    mineable = [kw for kw in feed["keywords"]
                if kw["status"] == "pass" and not kw.get("drained")]
    if not mineable:
        return None
    return max(mineable,
               key=lambda kw: (kw.get("pass_rate") or 0.0,
                               kw.get("volume") or 0))


def assemble(feed_id: str, goal: int | None = None, max_cycles: int | None = None) -> None:
    """Work one feed toward its goal. Runs until ready, stalled, or cycle cap.

    Post judgement only — the pool is fixed at feed creation (harvest.py);
    the loop plays it out:

    - **Mine** the best approved keyword that still has unfetched supply, else
    - **Explore** a candidate keyword, picked by steering from the ledger (or
      the oldest if steering says nothing usable), else
    - **Stall** — the pool is spent; nothing new can be planted mid-crawl.

    The cycle cap bounds runs on a stubborn topic. See the other two modules
    for why the split exists: judge.py judges, harvest.py seeds.
    """
    goal = goal if goal is not None else state.FEEDS_GOAL
    max_cycles = max_cycles if max_cycles is not None else state.FEEDS_MAX_CYCLES
    feeds = state.load_feeds()
    feed = feeds.get(feed_id)
    if feed is None:
        return
    if feed.get("status") == "ready":
        return
    feed["status"] = "assembling"
    state.save_feeds(feeds)

    tried_this_run: set[str] = set()
    while True:
        feed["cycles"] = feed.get("cycles", 0) + 1
        if len(feed["posts"]) >= goal:
            feed["status"] = "ready"
            state.save_feeds(feeds)
            print(f"[{feed_id[:10]}] READY — {len(feed['posts'])}/{goal} posts",
                  file=sys.stderr)
            return
        if feed["cycles"] > max_cycles:
            feed["status"] = "stalled"
            feed["note"] = f"cycle cap ({max_cycles}) hit with {len(feed['posts'])} posts"
            state.save_feeds(feeds)
            print(f"[{feed_id[:10]}] STALLED ({feed['note']})", file=sys.stderr)
            return

        try:
            mine = _best_mineable(feed)
            if mine:
                mine_keyword(feed, mine)
            else:
                jobs = [kw for kw in feed["keywords"]
                        if kw["status"] == "candidate"
                        and kw["keyword"] not in tried_this_run]
                if jobs:
                    kw = _steer(feed, jobs, tried_this_run)
                    if not kw:
                        kw = jobs[0]
                    tried_this_run.add(kw["keyword"])
                    try_keyword(feed, kw)
                else:
                    feed["status"] = "stalled"
                    feed["note"] = "candidate pool exhausted"
                    state.save_feeds(feeds)
                    print(f"[{feed_id[:10]}] STALLED — nothing left to try",
                          file=sys.stderr)
                    return
        except ClassifyError as e:
            # A bad LLM answer should not stall the feed — note and retry
            # the same cycle next time.
            feed["note"] = f"classification failed: {e}"
        except apppass.AuthError as e:
            feed["note"] = f"search account refused: {e}"
            login_notice()
        except BskyError as e:
            feed["note"] = f"search failed: {e}"
        except Exception as e:  # noqa: BLE001 — a bad keyword must not end the feed
            feed["note"] = f"{type(e).__name__}: {e}"

        state.save_feeds(feeds)


def _steer(feed: dict, jobs: list[dict], tried: set[str]) -> dict | None:
    """Ask the model which candidate to try next. Pure selection — nothing is
    judged here. Returns the picked keyword, or None when the model chose
    stop or gave an unusable answer (the caller falls back to the oldest)."""
    decision = judge.steer(feed, jobs, tried)
    if not decision:
        return None
    action = decision.get("action", "try")
    if action not in ("try",):
        return None
    pick = decision.get("pick", "")
    kw = next((k for k in jobs if k["keyword"].lower() == pick.lower()), None)
    return kw


def _session_hint(err: str) -> bool:
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="run one cycle and exit")
    parser.add_argument("--candidates", type=int, default=1,
                        help="how many untried keywords one cycle tries")
    parser.add_argument("--feed", default="",
                        help="only crawl this feed's keywords")
    parser.add_argument("--goal", action="store_true",
                        help="assemble all feeds toward their goal, once")
    parser.add_argument("--interval", type=int, default=1800,
                        help="seconds between cycles (loop mode)")
    args = parser.parse_args(argv)

    if not apppass.configured():
        print("No search account: set INDEX_BLUESKY_HANDLE and "
              "INDEX_BLUESKY_APP_PASSWORD in .env (an app password for the "
              "crawler's own account).", file=sys.stderr)
        sys.exit(1)

    feeds = state.load_feeds()
    if not feeds:
        print("No feeds yet. Create one first: "
              "python3 feeds/request.py add \"posts about ...\"",
              file=sys.stderr)
        if args.once:
            return
        time.sleep(args.interval)

    if args.goal:
        for feed_id in [f for f in feeds if not args.feed or f == args.feed]:
            assemble(feed_id)
        return

    processed = 0
    hit_login_error = False
    tried_this_run = set()
    while True:
        jobs = [
            (feed["id"], kw)
            for feed in feeds.values()
            if (not args.feed or feed["id"] == args.feed)
            for kw in feed["keywords"]
            if kw["status"] == "candidate" and kw["keyword"] not in tried_this_run
        ]
        if not jobs:
            total = sum(len(f["posts"]) for f in feeds.values())
            print("no untried keywords left. " + (f"Showing {total} post(s) "
                  f"across {len(feeds)} feed(s)." if feeds else ""),
                  file=sys.stderr)
            if args.once:
                return
            time.sleep(args.interval)
            continue

        feed_id, kw = jobs[0]
        feed = feeds[feed_id]
        print(f"[{feed_id[:10]}] trying keyword: {kw['keyword']!r}",
              file=sys.stderr)
        try:
            try_keyword(feed, kw)
        except BskyError as e:
            kw["note"] = f"search failed: {e}"
            if _session_hint(str(e)):
                kw["status"] = "candidate"
                hit_login_error = True
            else:
                kw["status"] = "error"
        except apppass.AuthError as e:
            kw["note"] = f"search account refused: {e}"
            kw["status"] = "candidate"
            hit_login_error = True
        except ClassifyError as e:
            kw["retries"] = kw.get("retries", 0) + 1
            kw["note"] = f"classifier failed (retry {kw['retries']}): {e}"
            if kw["retries"] >= state.MAX_CLASSIFY_RETRIES:
                kw["status"] = "error"
            else:
                kw["status"] = "candidate"
        except apppass.BskySearchError as e:
            kw["status"] = "error"
            kw["note"] = f"search failed: {e}"
        except Exception as e:  # noqa: BLE001 — a bad keyword must not end the feed
            kw["status"] = "error"
            kw["note"] = f"{type(e).__name__}: {e}"

        tried_this_run.add(kw["keyword"])
        state.save_feeds(feeds)
        summary(feed_id, kw, [])
        processed += 1

        if hit_login_error:
            login_notice()
            return
        if processed >= args.candidates:
            break

    if args.once:
        return
    time.sleep(args.interval)


def summary(feed_id: str, kw: dict, new_keywords: list[dict]) -> None:
    rate = kw.get("pass_rate")
    rate = f"{rate:.0%}" if rate is not None else "?"
    note = f"  ({kw['note']})" if kw.get("note") else ""
    extra = ""
    if kw["status"] == "pass" and new_keywords:
        extra = f"  -> new keywords: {', '.join(c['keyword'] for c in new_keywords[:5])}"
    elif kw["status"] == "fail":
        extra = "  (did not meet the criteria)"
    print(f"  {kw['status']:>7}  {kw['keyword']!r}  fit {rate} "
          f"({kw.get('posts_confirmed', 0)} of {kw.get('posts_seen', 0)}) "
          f"[{feed_id[:10]}]{extra}{note}", file=sys.stderr)


if __name__ == "__main__":
    main()