#!/usr/bin/env python3
"""Search Bluesky accounts by name, handle or bio text. Prints one line per
account — see actor_index.format_actor for the format.

The bio is searched too, not just the handle and display name, which is what
makes accounts findable by what they say about themselves ("permaculture",
"formerly @foo on instagram") rather than only by what they're called.

    python3 search_actors.py permaculture
    python3 search_actors.py "time banking" --limit 50
"""
import argparse
import sys

from actor_index import print_actors
from bsky import BskyError, get


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="a name, handle, or bio term")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    data = get("app.bsky.actor.searchActors", {"q": args.query, "limit": args.limit})
    print_actors(data.get("actors", []))


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"actor search failed: {e}", file=sys.stderr)
        sys.exit(1)
