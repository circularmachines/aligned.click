#!/usr/bin/env python3
"""Fetch a Bluesky post thread (a conversation) from a post URI. Prints the
whole thread — ancestors, the focused post, and the reply tree — one indexed
line per post, indented by depth. The focused post is marked with ►.

    python3 thread_posts.py at://did:plc:.../app.bsky.feed.post/xyz
    python3 thread_posts.py at://... --depth 4 --parent-height 20

Indices are shared with the other post tools (search/author), so the same
post keeps the same [N] everywhere. Reply with just `[N]` to show a post.
"""
import argparse
import sys

from bsky import BskyError, get
from post_index import assign_indices, extract, format_line


def get_post_thread(uri: str, depth: int, parent_height: int) -> dict:
    data = get("app.bsky.feed.getPostThread", {
        "uri": uri,
        "depth": depth,
        "parentHeight": parent_height,
    })
    return data["thread"]


def flatten(thread: dict) -> list[tuple[int, dict]]:
    """Walk the thread into a flat (depth, post) list in reading order:
    oldest ancestor first, then the focused post, then the reply tree DFS.
    Only real posts are kept — blocked/not-found nodes have no `post`."""
    # Ancestors: follow the parent chain up, then reverse to oldest-first.
    ancestors = []
    node = thread.get("parent")
    while node and "post" in node:
        ancestors.append(node["post"])
        node = node.get("parent")
    ancestors.reverse()

    rows: list[tuple[int, dict]] = [(i, post) for i, post in enumerate(ancestors)]
    base = len(ancestors)  # the focused post's depth
    rows.append((base, thread["post"]))

    def walk(reply_parent: dict, depth: int) -> None:
        for reply in reply_parent.get("replies") or []:
            if "post" not in reply:
                continue
            rows.append((depth, reply["post"]))
            walk(reply, depth + 1)

    walk(thread, base + 1)
    return rows


def print_thread(rows: list[tuple[int, dict]], focus_uri: str) -> None:
    extracted = [(depth, extract(post)) for depth, post in rows]
    indices = assign_indices([p["uri"] for _, p in extracted])
    for depth, p in extracted:
        marker = "►" if p["uri"] == focus_uri else " "
        prefix = f"{'  ' * depth}{marker} "
        print(format_line(indices[p["uri"]], p, prefix=prefix))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri", help="at:// URI of any post in the thread")
    parser.add_argument("--depth", type=int, default=6, help="how many reply levels below the post")
    parser.add_argument("--parent-height", type=int, default=10, help="how many ancestors above the post")
    args = parser.parse_args()

    thread = get_post_thread(args.uri, args.depth, args.parent_height)
    if "post" not in thread:
        kind = thread.get("$type", "").split("#")[-1] or "unavailable"
        print(f"thread unavailable ({kind}) for {args.uri}", file=sys.stderr)
        sys.exit(1)
    print_thread(flatten(thread), thread["post"]["uri"])


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
