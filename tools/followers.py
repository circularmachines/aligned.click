#!/usr/bin/env python3
"""List the accounts that follow a Bluesky user (walks the follow graph inward).

    python3 followers.py alice.bsky.social --limit 50
"""
import argparse
import sys

from actor_index import print_actors
from bsky import BskyError, get


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor", help="handle or DID whose followers to list")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    data = get("app.bsky.graph.getFollowers", {"actor": args.actor, "limit": args.limit})
    print_actors(data.get("followers", []))


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"followers fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
