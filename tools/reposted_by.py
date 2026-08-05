#!/usr/bin/env python3
"""List the accounts that reposted a specific post (walks the engagement graph).

    python3 reposted_by.py at://did:plc:.../app.bsky.feed.post/xyz --limit 50
"""
import argparse
import sys

from actor_index import print_actors
from bsky import BskyError, get


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri", help="at:// URI of the post")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    data = get("app.bsky.feed.getRepostedBy", {"uri": args.uri, "limit": args.limit})
    print_actors(data.get("repostedBy", []))


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"reposts fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
