#!/usr/bin/env python3
"""Search Bluesky posts. Prints one indexed line per post — see
post_index.print_indexed for the exact format and how to reference a post.

Takes one or more terms; each term may be several words. Multi-word terms are
matched as exact phrases, and results must contain every term:

    python3 search_posts.py "solar punk" --limit 10
    python3 search_posts.py "mechanical design" "open source" --limit 10
"""
import argparse
import sys

from bsky import BskyError, get
from post_index import print_indexed


def build_query(terms: list[str]) -> str:
    """Combine terms into a Bluesky `q` string: multi-word terms become exact
    phrases (quoted), and space-joining them requires all terms to appear."""
    parts = []
    for term in terms:
        term = term.strip().strip('"')
        if not term:
            continue
        parts.append(f'"{term}"' if " " in term else term)
    return " ".join(parts)


def search_posts(query: str, limit: int) -> list[dict]:
    return get("app.bsky.feed.searchPosts", {"q": query, "limit": limit})["posts"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="+", help="one or more search terms (each may be multi-word)")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    query = build_query(args.terms)
    # Name the terms back on an empty result, and say why it can be empty:
    # results must contain EVERY term, so a list of related topics matches
    # almost nothing. Without this the model sees a blank response and guesses.
    empty = (
        f"(no posts contain all of: {', '.join(args.terms)} — "
        "every term must appear in the same post, so search one topic at a time)"
        if len(args.terms) > 1
        else f"(no posts matched: {args.terms[0]})"
    )
    print_indexed(search_posts(query, args.limit), empty=empty)


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"search failed: {e}", file=sys.stderr)
        sys.exit(1)
