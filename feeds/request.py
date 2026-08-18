#!/usr/bin/env python3
"""Create feed requests — the product's front door.

    python3 feeds/request.py add "posts about people repairing stuff"
    python3 feeds/request.py list
    python3 feeds/request.py show <id>
    python3 feeds/request.py remove <id>

`add` is the publish button. The phrase the reader types *is* the feed — no
decoding step:

1. the literal answer becomes the criteria the quality check judges posts
   against (see judge.criteria);
2. a few keywords are planted for it, harvested from the answer itself
   (feed-creation only — see harvest.py);
3. crawl.py works the pool continuously: the posts that fit are stored on the
   feed ready to be shown by `show`.

`show` prints those posts, one line each. `remove` drops a feed entirely — its
keywords and posts go with it, since nothing is shared.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT.parent / "cause"))

import state  # noqa: E402
import harvest  # noqa: E402
from classify import ClassifyError  # noqa: E402


def add(text: str) -> dict:
    """Create the feed, plant its first keywords, and report."""
    if not text.strip():
        raise ValueError("the request is empty — say what kind of posts you "
                         "want to see more of.")

    feed = state.new_feed(text)
    feeds = state.load_feeds()
    seeds = harvest.seed_keywords(text)
    feed["keywords"].extend(state.new_from([], seeds, "seed"))
    feeds[feed["id"]] = feed
    state.save_feeds(feeds)
    return {"feed": feed, "seeds": seeds}


def list_feeds() -> None:
    feeds = state.load_feeds()
    if not feeds:
        print("no feeds yet. Create one: python3 feeds/request.py add \"...\"",
              file=sys.stderr)
        return
    print(f"{len(feeds)} feed(s):")
    for fid, feed in sorted(feeds.items()):
        candidates = sum(1 for k in feed["keywords"] if k["status"] == "candidate")
        print(f"  {fid[:19]}  \"{feed['text']}\"  "
              f"{len(feed['posts'])} post(s), {len(feed['keywords'])} "
              f"keyword(s), {candidates} to try")


def show(fid: str) -> None:
    feeds = state.load_feeds()
    feed = feeds.get(fid) or next(
        (f for f in feeds.values() if f["id"].startswith(fid)), None)
    if not feed:
        print(f"no feed with id {fid}.", file=sys.stderr)
        sys.exit(1)
    posts = list(feed["posts"].values())
    print(f"\"{feed['text']}\" — {len(posts)} post(s):")
    if not posts:
        print("  (empty — crawl it: python3 feeds/crawl.py --once, or wait "
              "for the loop)", file=sys.stderr)
        return
    for i, p in enumerate(posts, 1):
        print(f"  {i}. @{p['handle']}  {p['createdAt']}  {p['uri']}")
        print(f"     {' '.join((p['text'] or '').split())[:200]}")
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
            print(f"  planted {len(result['seeds'])} keyword(s): "
                  f"{', '.join(result['seeds'])}")
            print("  now crawl it: python3 feeds/crawl.py --once")
            print("  then show posts: python3 feeds/request.py show "
                  f"{feed['id'][:19]}")
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