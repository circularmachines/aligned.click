#!/usr/bin/env python3
"""Fetch the posts an account has liked. Prints one indexed line per post —
see post_index.print_indexed for the exact format and how to reference a post.

Bluesky only serves a repo's likes to that repo's owner, so this works for the
logged-in account only; another handle comes back as an HTTP error.

    python3 liked_posts.py alice.bsky.social --limit 20
"""
import argparse
import sys

from bsky import BskyError, get
from post_index import print_indexed


def get_actor_likes(actor: str, limit: int) -> list[dict]:
    data = get("app.bsky.feed.getActorLikes", {"actor": actor, "limit": limit})
    # Same feed envelope as getAuthorFeed: [{post, reason?}, ...]
    return [item["post"] for item in data.get("feed", []) if item.get("post")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    print_indexed(get_actor_likes(args.actor, args.limit))


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"likes fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
