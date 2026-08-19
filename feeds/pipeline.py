#!/usr/bin/env python3
"""The feed pipeline — one run per criteria.

When a reader writes a criteria, one run of this script does this:

1. **Embed the criteria** and cosine-search the embedded post store
   (index_db.posts) for the top-SEED_TOP_N posts closest to it, skipping the
   posts this feed has already judged;
2. **Grade the ungraded ones** — `judge.quality()` gives each post a general
   quality score (0-10), a property of the post itself, computed once and
   stored on it, so every new feed reuses the same grades without another
   call;
3. **Judge fit** — `judge.quality_check()` decides the binary per-feed
   membership against the criteria, and the fittings are kept on the feed
   record (feeds.json).

The store is grown by a separate keyword crawler (later work, mirroring
index/crawl.py): nothing is searched or embedded here at submit time. A feed
on an empty store finds no candidates — it lights up as the crawler indexes
terms, and re-running this script picks up what the crawler has since added.

    python3 feeds/pipeline.py <id>            # one run for an existing feed
    python3 feeds/pipeline.py --new "text"    # create a feed and run it

The chat calls talk to GreenPT v4 flash through cause/classify's _completion;
embeddings use feeds/embed.py.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
sys.path.insert(0, str(ROOT))

import state  # noqa: E402
import embed  # noqa: E402
import index_db  # noqa: E402
import judge  # noqa: E402
from classify import ClassifyError  # noqa: E402


def _log(*parts):
    print(f"[{time.strftime('%H:%M:%S')}] " + " ".join(str(p) for p in parts),
          file=sys.stderr, flush=True)


def run(feed_id: str, feeds: dict | None = None) -> dict:
    """One pipeline run for a feed: seed → grade → judge fit. Returns the
    feed after the run. `feeds` is the caller's loaded state (so web.py and
    the CLI share one write); when omitted it is loaded here."""
    feeds = feeds if feeds is not None else state.load_feeds()
    feed = feeds.get(feed_id)
    if feed is None:
        raise ValueError(f"no feed with id {feed_id}.")

    criteria_text = feed["text"]
    _log(f"pipeline for {feed_id}: \"{criteria_text}\"")
    vec = embed.embed([criteria_text])[0]

    seen = set(feed.get("seen") or [])
    seed = index_db.similar_posts(vec, state.SEED_TOP_N, exclude_uris=seen)
    candidates = [dict(s) for s in seed]
    _log(f"seeded top-{len(candidates)} posts by criteria similarity "
         f"(skipping {len(seen)} already judged by this feed)")
    if not candidates:
        _log("store has nothing close to this criteria that this feed has "
             "not judged yet — the keyword crawler has to index terms first")
    for c in candidates:
        c.pop("embedding", None)

    ungraded = [c for c in candidates if not c.get("graded")]
    if ungraded:
        _log(f"grading {len(ungraded)} post(s) — general quality (0-10), "
             "reused by every feed")
        grades = judge.quality(ungraded)
        index_db.mark_graded([(c["uri"], g.get("grade"), g.get("why"))
                              for c, g in zip(ungraded, grades)])
        for c, g in zip(ungraded, grades):
            c["grade"] = g.get("grade", 0)
    else:
        _log(f"all {len(candidates)} seed(s) already graded — reusing stored "
             "grades")

    fit_scores = judge.quality_check(candidates,
                                     feed.get("criteria") or feed["text"])
    confirmed = judge.campaign_posts(candidates, fit_scores)
    _log(f"judged fit for {len(candidates)} candidate(s); "
         f"{len(confirmed)} belong in this feed")
    for entry in confirmed:
        entry["found_by"] = entry.get("keyword") or ""
        feed["posts"][entry["uri"]] = entry

    feed["suggested"] = confirmed
    feed["seen"] = list(seen | {c["uri"] for c in candidates})
    feed["rounds"] = feed.get("rounds", 0) + 1
    feed["note"] = None
    state.save_feeds(feeds)
    return feed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("id", nargs="?", default="",
                        help="the feed's id (or its unique prefix)")
    parser.add_argument("--new", default="",
                        help="create a feed from this criteria, then run it")
    args = parser.parse_args(argv)

    feeds = state.load_feeds()

    if args.new:
        import request  # imported here: request.add runs this module, so a
                        # top-level import would be a cycle
        text = args.new.strip()
        if not text:
            print("the criteria is empty — say what kind of posts you want "
                  "to see more of.", file=sys.stderr)
            sys.exit(1)
        result = request.add(text)
        feed = result["feed"]
        print(f"created feed {feed['id']}", file=sys.stderr)
        print(f"  criteria: {feed['text']}")
        _report(feed)
        return

    feed_id = next((f for f in feeds
                    if f == args.id or f.startswith(args.id)), None)
    if not feed_id:
        print(f"no feed with id {args.id}.", file=sys.stderr)
        sys.exit(1)

    try:
        feed = run(feed_id, feeds)
    except (ValueError, ClassifyError) as e:
        print(f"run failed: {e}", file=sys.stderr)
        sys.exit(1)
    _report(feed)


def _report(feed: dict) -> None:
    print(f"\"{feed['text']}\" — round {feed.get('rounds', 0)}, "
          f"{len(feed.get('posts') or {})} post(s) on the feed, "
          f"{len(feed.get('suggested') or [])} judged this run:")
    for p in feed.get("suggested") or []:
        print(f"  - @{p.get('handle')}  {p.get('found_by') or '?'!r}  {p['uri']}")
        print(f"      {' '.join((p.get('text') or '').split())[:200]}")
        if p.get("why"):
            print(f"      why: {p['why']}")
    posts = index_db.post_counts()
    print(f"  post store: {posts}")


if __name__ == "__main__":
    main()