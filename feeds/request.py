#!/usr/bin/env python3
"""Create feed requests — the product's front door.

    python3 feeds/request.py add "posts about people repairing stuff"
    python3 feeds/request.py list
    python3 feeds/request.py show <id>
    python3 feeds/request.py remove <id>

`add` is the publish button. The phrase the reader types *is* the feed — no
decoding step:

1. the literal answer becomes the criteria the quality check judges posts
   against (see crawl.criteria);
2. a few keywords are planted for it (see judge.harvest_keywords), seeded
   from the answer itself;
3. crawl.py works the pool: the posts that fit are stored on the feed ready to
   be shown by `show`.

`show` prints those posts, one line each. `remove` drops a feed entirely — its
keywords and posts go with it, since nothing is shared.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT.parent / "cause"))

import state  # noqa: E402
from classify import ClassifyError, _completion, _find_json_array  # noqa: E402


def seed_keywords(text: str) -> list[str]:
    """The first search terms for a brand-new feed, from its literal answer.

    The index experiment started from a hand-written seeds.txt; a general feed
    builder cannot — the answer is the seed. The same call shape as the
    judge's harvest (judge.harvest_keywords), just aimed at the request text
    instead of example posts.
    """
    content = _completion([
        {"role": "system", "content":
            "You give a brand-new Bluesky feed its first search terms. Given "
            "what the reader asked to see, name 1-3 word search terms "
            "(lowercase, no quotes) that would retrieve that kind of post.\n"
            "How a term is matched, exactly: a single word is searched as that "
            "word; a multi-word term is searched as the exact phrase in that "
            "order — it does NOT match posts that only contain some of those "
            "words. There is no OR-ing and no word-by-word matching. So a "
            "term like \"repair cafe\" retrieves posts containing the phrase "
            "\"repair cafe\", and a term like \"mending\" retrieves posts "
            "containing that word. Name phrases that genuinely occur together "
            "in that order; when in doubt, prefer a good single word. "
            "Skip brand names and specific places."},
        {"role": "user", "content":
            f"The request: {text}\n\nReturn ONLY a JSON array of search "
            "terms, 4 to 8 of them. No prose around the JSON."},
    ])
    return _parse_terms(content)


def _parse_terms(content: str) -> list[str]:
    try:
        terms = json.loads(_find_json_array(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"terms JSON did not parse ({e})") from None
    if not isinstance(terms, list):
        raise ClassifyError("terms call returned an object, not an array")
    cleaned: list[str] = []
    for t in terms:
        if not isinstance(t, str):
            continue
        t = t.strip().strip('"').lower()
        if 1 < len(t) <= 40 and t not in cleaned:
            cleaned.append(t)
    return cleaned


def add(text: str) -> dict:
    """Create the feed, plant its first keywords, and report."""
    if not text.strip():
        raise ValueError("the request is empty — say what kind of posts you "
                         "want to see more of.")

    feed = state.new_feed(text)
    feeds = state.load_feeds()
    seeds = seed_keywords(text)
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