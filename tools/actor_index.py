"""Formats a Bluesky actor (account) into one readable line for the model —
the actor-side counterpart to post_index. Actors are referenced by @handle
(feed the handle to author-posts, follows, etc.), so they need no [N] index.

Detailed profiles (from getProfile) carry follower/following/post counts;
list entries (from getFollows/getLikes/...) usually don't — both are handled.
"""


def _bio(desc: str) -> str:
    return " ".join((desc or "").split())[:100]


def format_actor(a: dict) -> str:
    """`@handle (Display Name) — did · N followers / M following / K posts · "bio"`
    (counts and bio omitted when absent)."""
    head = f"@{a.get('handle', '')}"
    name = (a.get("displayName") or "").strip()
    if name:
        head += f" ({name})"

    meta = []
    if a.get("did"):
        meta.append(a["did"])
    if a.get("followersCount") is not None:
        meta.append(
            f"{a.get('followersCount', 0)} followers / "
            f"{a.get('followsCount', 0)} following / "
            f"{a.get('postsCount', 0)} posts"
        )

    line = head
    if meta:
        line += " — " + " · ".join(meta)
    bio = _bio(a.get("description"))
    if bio:
        line += f' · "{bio}"'
    return line


def print_actors(actors: list[dict]) -> None:
    if not actors:
        print("(no accounts)")
        return
    for a in actors:
        print(format_actor(a))
