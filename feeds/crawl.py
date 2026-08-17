#!/usr/bin/env python3
"""The general feed builder's loop: for each feed, work its keyword pool.

One feed at a time, the same crank the index runs — search a keyword, judge
the posts against *this feed's* criteria (the literal answer), keep the posts
that fit, harvest new keywords from them. The judgment cargo is the feed's
own, in judge.py; the index is not imported.

    python3 feeds/crawl.py --once                # one cycle, exit
    python3 feeds/crawl.py --candidates 3        # three keywords this cycle
    python3 feeds/crawl.py --interval 1800       # loop forever, 30 min apart

State lives in feeds/feeds.json, one record per feed as described in state.py.
"""
import argparse
import json
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


def search_latest(term: str, limit: int) -> list[dict]:
    """Bluesky search, newest first, only posts from the last WINDOW_DAYS.

    The window is applied on the post's own createdAt, client-side. A
    multiword keyword is searched as the literal phrase. Two transports: the
    crawler's own app password when configured, else the OAuth sidecar.
    """
    import datetime

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
        days=state.WINDOW_DAYS)
    fresh: list[dict] = []
    for v in views:
        when = judge.parse_created(((v.get("record") or {}).get("createdAt") or ""))
        if when is None or when >= cutoff:
            fresh.append(v)
        if len(fresh) >= limit:
            break
    return fresh


def criteria(feed: dict) -> str:
    """The quality check's criteria for a feed: the literal answer, verbatim.

    This is the whole simplification. A feed request is not decoded into
    anything — the reader's words *are* the standard of fit, in the same shape
    the index's CRITERIA uses for its one cause.
    """
    return (
        "A post belongs in the feed when it matches, in the reader's own "
        "words, what they asked to see. The request:\n"
        f"{feed['text']}\n"
        "The subject or speaker is the kind of thing the request names. It "
        "does NOT belong when it is only vaguely related, an ad, news, or "
        "unrelated happenings. If you are unsure whether a post fits, it fits."
    )


def explore_keyword(feed: dict, kw: dict) -> list[dict]:
    """The quality check + harvest for one keyword of one feed.

    Mutates the feed record and the keyword; returns freshly harvested
    keywords (deduped against the feed's pool) so the caller adds them flat.
    The keyword is the unit of failure: errors mark it 'error' instead of
    killing the cycle.
    """
    term = kw["keyword"]
    kw["tested"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    views = search_latest(term, state.POSTS_PER_KEYWORD)
    kw["posts_seen"] = len(views)
    if not views:
        kw["status"] = "pass"
        kw["pass_rate"] = 0.0
        kw["note"] = f"no posts in the last {state.WINDOW_DAYS} days"
        return []

    candidates = [extract(v) for v in views]
    scores = judge.quality_check(candidates, criteria(feed))
    fitting = [s for s in scores if s.get("fit")]
    kw["pass_rate"] = len(fitting) / len(scores) if scores else 0.0
    kw["posts_confirmed"] = len(fitting)

    # Whatever the outcome, the fitting posts are the feed.
    for entry in judge.campaign_posts(candidates, scores):
        feed["posts"][entry["uri"]] = entry

    if kw["pass_rate"] >= state.PASS_RATE:
        kw["status"] = "pass"
        return state.new_from(
            feed["keywords"], judge.harvest_keywords(
                [candidates[s["i"]] for s in fitting], term), term) if fitting else []
    kw["status"] = "fail"
    return []


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
                        help="only crawl this feed's candidate keywords")
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

    processed = 0
    hit_login_error = False
    tried_this_run = set()
    while True:
        # The oldest feed with an untried keyword goes first, so a fresh feed
        # starts being filled instead of waiting behind mature ones. `--feed`
        # confines the cycle to one feed — that is what "Crawl one" on a card
        # must mean, or a click inexplicably works another subject's keywords.
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
        new_keywords: list[dict] = []
        try:
            new_keywords = explore_keyword(feed, kw)
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

        feed["keywords"].extend(new_keywords)
        tried_this_run.add(kw["keyword"])
        state.save_feeds(feeds)
        summary(feed_id, kw, new_keywords)
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