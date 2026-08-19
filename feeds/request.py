#!/usr/bin/env python3
"""Create feed requests — the product's front door.

    python3 feeds/request.py add "posts about sharing food"
    python3 feeds/request.py list
    python3 feeds/request.py show <id>
    python3 feeds/request.py remove <id>

`add` is the publish button. The phrase the reader types *is* the feed — no
decoding step — and one pipeline run happens immediately:

1. the literal answer becomes the criteria the per-post judge tests against
   (see judge.criteria);
2. the judge is seeded from criteria-similar posts already in the embedded
   post store and the fittings are kept on the feed (pipeline.py).

The store is grown separately — the keyword crawler (later work) indexes
terms; a feed on an empty store finds nothing until then.

`show` prints the feed the reader has built so far. `remove` drops a feed
entirely — its feed record goes with it; the global keyword/post stores
survive, since they are shared.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT.parent / "index"))
sys.path.insert(0, str(ROOT.parent / "cause"))
sys.path.insert(0, str(ROOT))

import state  # noqa: E402
import pipeline  # noqa: E402
from classify import ClassifyError  # noqa: E402


def add(text: str) -> dict:
    """Create the feed and run one pipeline pass: seed from the post store,
    judge. Nothing is searched or embedded here — that is the crawler's job."""
    if not text.strip():
        raise ValueError("the request is empty — say what kind of posts you "
                         "want to see more of.")

    feed = state.new_feed(text)
    feeds = state.load_feeds()
    feeds[feed["id"]] = feed
    state.save_feeds(feeds)
    pipeline.run(feed["id"], feeds)
    return {"feed": feed}


def list_feeds() -> None:
    feeds = state.load_feeds()
    if not feeds:
        print("no feeds yet. Create one: python3 feeds/request.py add \"...\"",
              file=sys.stderr)
        return
    print(f"{len(feeds)} feed(s):")
    for fid, feed in sorted(feeds.items()):
        included = len(feed.get("included") or {})
        suggested = len(feed.get("suggested") or [])
        print(f"  {fid[:19]}  \"{feed['text']}\"  "
              f"{included} kept, {len(feed['keywords'])} keyword(s), "
              f"{suggested} awaiting a verdict")


def show(fid: str) -> None:
    feeds = state.load_feeds()
    feed = feeds.get(fid) or next(
        (f for f in feeds.values() if f["id"].startswith(fid)), None)
    if not feed:
        print(f"no feed with id {fid}.", file=sys.stderr)
        sys.exit(1)
    included = feed.get("included") or {}
    print(f"\"{feed['text']}\" — {len(included)} kept post(s), round "
          f"{feed.get('rounds', 0)}:")
    if not included:
        print("  (empty — run the pipeline again: python3 feeds/pipeline.py "
              f"{feed['id'][:19]})", file=sys.stderr)
    for i, p in enumerate(included.values(), 1):
        print(f"  {i}. @{p.get('handle')}  {p.get('createdAt')}  {p['uri']}")
        print(f"     {' '.join((p.get('text') or '').split())[:200]}")
        if p.get("why"):
            print(f"     why: {p['why']}")


def remove(fid: str) -> None:
    feeds = state.load_feeds()
    feed = feeds.pop(fid, None)
    if not feed:
        print(f"no feed with id {fid}.", file=sys.stderr)
        sys.exit(1)
    state.save_feeds(feeds)
    print(f"removed feed {fid[:19]} (\"{feed['text']}\").")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="create a feed from a literal answer")
    p_add.add_argument("text", help="what you want to see, in your own words")

    sub.add_parser("list", help="list the feeds")

    p_show = sub.add_parser("show", help="show a feed's posts")
    p_show.add_argument("id", help="the feed's id (or its unique prefix)")

    p_remove = sub.add_parser("remove", help="drop a feed")
    p_remove.add_argument("id", help="the feed's id")

    args = parser.parse_args()

    try:
        if args.command == "add":
            result = add(args.text)
            feed = result["feed"]
            print(f"feed {feed['id']} created")
            print(f"  answer: {feed['text']}")
            print(f"  {len(feed.get('posts') or {})} post(s) judged fit so far — "
                  f"run again to pick up what the crawler has since indexed: "
                  f"python3 feeds/pipeline.py {feed['id'][:19]}")
        elif args.command == "list":
            list_feeds()
        elif args.command == "show":
            show(args.id)
        elif args.command == "remove":
            remove(args.id)
    except ValueError as e:
        print(f"{e}", file=sys.stderr)
        sys.exit(1)
    except ClassifyError as e:
        print(f"failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()