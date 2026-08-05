#!/usr/bin/env python3
"""Get Bluesky profile(s) — the node metadata for social-graph work: follower /
following / post counts and bio. Accepts one or more handles or DIDs (up to 25).

    python3 profile.py alice.bsky.social
    python3 profile.py alice.bsky.social bob.bsky.social
"""
import argparse
import sys

from actor_index import print_actors
from bsky import BskyError, get


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actors", nargs="+", help="one or more handles or DIDs")
    args = parser.parse_args()
    data = get("app.bsky.actor.getProfiles", {"actors": args.actors})
    print_actors(data.get("profiles", []))


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"profile fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
