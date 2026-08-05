#!/usr/bin/env python3
"""Show one Bluesky account as a card in the chat.

The people half of what show_post.py does for posts, and it exists for the same
reason: describing an account in prose means spending sentences on the handle,
the bio and the follower count, every one of which the reader can see perfectly
well once the card is on screen. What the model has to supply is the part that
isn't on the card — why *this* person.

**Handles go in, a DID comes out.** A handle is a mutable pointer and PLAN.md
records the model trusting one where it shouldn't; more immediately, an account
that doesn't exist has to fail here, loudly, rather than render as an empty card
the reader is left to interpret. So the actor is resolved through getProfile
first: that both proves it exists and yields the DID the card is drawn from.

**One account per call**, for the reason show_post takes one post — see PLAN.md
workstream 6.

    python3 show_actor.py alice.bsky.social
"""
import argparse
import sys

import render
from actor_index import format_actor
from bsky import BskyError, get


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor", help="a handle or DID, e.g. alice.bsky.social")
    args = parser.parse_args()

    actor = args.actor.strip().lstrip("@")

    try:
        profile = get("app.bsky.actor.getProfile", {"actor": actor})
    except BskyError as e:
        # A handle the model invented is the common case here, and it needs to
        # hear that rather than see a card quietly not appear.
        print(
            f"Not shown: no account '{args.actor}' — {e}\n"
            "Check the handle against the output of a search or graph tool; only "
            "an account that exists can be shown."
        )
        return

    did = profile.get("did")
    if not did:
        print(f"Not shown: '{args.actor}' resolved to no DID, so there is nothing to draw.")
        return

    # The receipt tells the model exactly what the reader can now see, in the
    # same one-line form the graph tools print, so "don't repeat this" has
    # something concrete attached to it rather than being a rule in the abstract.
    print(f"Showing this account as a card in the chat:\n  {format_actor(profile)}")
    print(
        "\nEverything on that line is now on screen — the name, the handle, the "
        "bio and the counts — so none of it needs saying again.\n"
        "Write why this person is worth the creator's attention now, before "
        "showing another account or doing anything else. What you write next "
        "appears directly under this card; anything saved for the end of the turn "
        "arrives detached from the person it is about."
    )
    render.emit(
        "actor",
        # The DID, not the handle: it is what the card is drawn from and it does
        # not change under us between now and the render.
        did=did,
        handle=profile.get("handle") or actor,
        name=(profile.get("displayName") or "").strip(),
        # The counts come from here rather than from the card, which derives its
        # own by enumerating records and undercounts badly — 12.7M against the
        # 34.3M the appview reports for @bsky.app, and "500+ posts" for an
        # account with 802. These are the numbers the strategist's judgment
        # rests on, so they have to be the real ones.
        followers=profile.get("followersCount"),
        following=profile.get("followsCount"),
        # Not `posts`: that name means an array in the posts payload, and the
        # collision has now been read as one twice — once taking a whole turn
        # of the UI down, once here.
        post_count=profile.get("postsCount"),
    )


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        print(f"could not show the account: {e}", file=sys.stderr)
        sys.exit(1)
