#!/usr/bin/env python3
"""Fetch a Bluesky user's posts. Prints one indexed line per post — see
post_index.print_indexed for the exact format and how to reference a post.

    python3 author_posts.py alice.bsky.social --limit 10
    python3 author_posts.py alice.bsky.social --replies
"""
import argparse
import sys

from bsky import BskyError, get
from post_index import print_indexed


def get_author_feed(actor: str, limit: int, replies: bool) -> list[dict]:
    data = get("app.bsky.feed.getAuthorFeed", {
        "actor": actor,
        "limit": limit,
        "filter": "posts_with_replies" if replies else "posts_no_replies",
    })
    return [item["post"] for item in data.get("feed", [])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--replies", action="store_true")
    args = parser.parse_args()

    print_indexed(get_author_feed(args.actor, args.limit, args.replies))


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
