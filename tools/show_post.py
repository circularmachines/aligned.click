#!/usr/bin/env python3
"""Show one Bluesky post as a card in the chat, in the mode the moment calls for.

Takes an `[N]` index the model has already been shown by search-posts,
author-posts, thread-posts or liked-posts, resolves it back to an at:// URI and
emits a render payload the UI turns into a live post card.

The index is the input, not the output. It's the one thing a weak model can
reproduce reliably — it is a few digits, it was on screen a moment ago, and
getting it wrong fails loudly here instead of silently rendering someone else's
post. Nothing about the URI ever passes through the model.

**One post per call, deliberately.** Told to show two posts, the model passes
both and writes about both underneath, which stacks the cards and separates
every note from the post it is about. Taking a single ref makes the interleaving
structural instead of a rule: card, comment, card, comment. Same argument as the
tool existing at all — see PLAN.md workstream 6.

**The mode carries the intention.** A post shown for its own sake and a post
shown because the creator ought to answer it are different things on screen, and
that difference used to live only in the prose underneath ("you could reply
something like…") — where it is a suggestion nobody can act on. So the call says
which:

- `default` — the post, with what you can do with it: reply, repost, like.
- `reply` — the post with a reply box, prefilled from `--text` when the agent
  has a reply to propose. The creator edits it and sends it themselves.
- `repost` — the post with a repost box, prefilled the same way. Sending it
  empty reposts plainly; sending it written-in quotes the post.

A proposed reply is a post like any other, so `--text` is counted against the
same 300-grapheme limit a draft is (see graphemes.py) and the count travels with
the payload.

    python3 show_post.py 3
    python3 show_post.py 3 --mode reply --text "Vi gjorde samma sak i verkstan…"
"""
import argparse

import graphemes
import render
from post_index import resolve

# What the model is told once the card is drawn. A standing rule in AGENTS.md is
# thousands of tokens back by the time it matters; this arrives in the moment it
# is deciding what to do next, which is the only moment it can act on it. Both
# halves are here — say something new, and say it *now* — because both failed in
# observed runs with the rule in the instructions alone.
SEEN = ("The reader now sees the post itself — its author, its date, its full "
        "text and its pictures — so none of that needs saying again.")

NEXT = ("Write what you have to add about it now, before showing another post "
        "or doing anything else, to keep the discussion chronological. What you "
        "write next appears directly under this card; anything saved for the end "
        "of the turn arrives detached from the post it is about.")

MODES = {
    "default": SEEN + "\n" + NEXT,
    "reply": (
        SEEN + "\nUnder it is a reply box already holding the reply you passed, "
        "which the creator can edit and send. So don't write that reply out again "
        "in your own words — it is on screen. Say why this reply, and why now.\n"
        + NEXT
    ),
    "repost": (
        SEEN + "\nUnder it is a repost box holding the comment you passed, which "
        "the creator can edit, clear to repost the post plainly, or send as a "
        "quote. So don't write the comment out again — say why this post is worth "
        "putting in front of their audience.\n" + NEXT
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", type=int, help="the post index to show, e.g. 3")
    parser.add_argument("--mode", choices=sorted(MODES), default="default",
                        help="what the card is for: default, reply or repost")
    parser.add_argument("--text", default="",
                        help="prefill for the reply or quote box")
    args = parser.parse_args()

    uri = resolve([args.ref]).get(args.ref)

    # An index that resolves to nothing is the model inventing one, and it has
    # to hear about it — a silently missing card reads as a rendering failure
    # and it will try again with the same wrong number.
    if not uri:
        print(
            f"Not shown: [{args.ref}] — no post has been listed under that index "
            "here. Only an index a search or feed tool printed in this workspace "
            "can be shown; find the post again and use the index from that output."
        )
        return

    text = args.text.strip()
    lines = [f"Showing [{args.ref}] as a card in the chat: {uri}"]

    if args.mode == "default":
        if text:
            # Said out loud rather than dropped quietly: text with no box to put
            # it in means the model meant to propose something and the creator
            # is never going to see it.
            lines.append(
                "  Ignored the text you passed — a default card has no box to put "
                "it in. Call again with mode 'reply' or 'repost' to propose it."
            )
            text = ""
    else:
        box = "reply box" if args.mode == "reply" else "quote box"
        if not text:
            lines.append(f"  An empty {box}, for the creator to write in themselves.")
        else:
            count = graphemes.count(text)
            lines.append(
                f"  {box.capitalize()} prefilled: {count}/{graphemes.LIMIT} graphemes"
                + (f" — {count - graphemes.LIMIT} OVER THE LIMIT, this cannot be "
                   "sent as written. Shorten it and show the post again."
                   if count > graphemes.LIMIT else "")
            )

    print("\n".join(lines))
    print("\n" + MODES[args.mode])

    render.emit(
        "posts",
        posts=[{"ref": args.ref, "uri": uri}],
        mode=args.mode,
        text=text,
        limit=graphemes.LIMIT,
    )


if __name__ == "__main__":
    main()
