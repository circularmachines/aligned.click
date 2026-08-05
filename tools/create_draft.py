#!/usr/bin/env python3
"""Show a post you are proposing as an editable draft card in the chat.

A proposed post is a **draft**, not a paragraph describing one. So this renders
the thing itself: the text in a box that can be edited in place, and a live
count against the 300-grapheme limit. Same inversion as show_post.py — the
model calls a tool and the UI renders its output — and for the same reason: a
tool call is the channel a weak model is most reliable in.

Two things have to be right, and neither is the chrome:

- **The grapheme count** (see graphemes.py). A draft over 300 cannot be posted
  at all, and nothing else about the card matters as much.
- **The facets.** A post is not what its raw text looks like: a URL becomes a
  link card and `@x.bsky.social` becomes a live mention, so a draft reviewed as
  flat text is a review of something that will not be published.

A draft must read as *recognisably a Bluesky post, visibly a draft*. These
cards sit next to real ones, and mistaking a proposal for something already
published is the one confusion that must not happen — hence the dashed edge
and the label, which a real post never has.

**Nothing here publishes anything, and no tool can.** The card's Post button is
disabled until an account is connected; publishing is something a person does,
from their own session, on text they have read. The name is `create-draft`
rather than `create-post` for that reason: a tool called create-post invites a
model to report that it posted something, which would be a lie.

Text only for now. Images need somewhere to come from — a blob on the author's
own PDS — and that arrives with the publish path, not before it.

    python3 create_draft.py --text "…"
"""
import argparse
import re
import sys
import unicodedata

import graphemes
import render

# Deliberately looser than atproto's own facet detection, because this is for
# *display*: better to show a link they will have to check than to render a
# live URL as flat text and have the card misrepresent the post.
LINK_RE = re.compile(r"https?://\S+|(?<![\w@.])[\w-]+\.[a-z]{2,}(?:/\S*)?", re.I)
# The lookbehind is the whole difference between a mention and an email
# address: without it `foo@bar.com` highlights `@bar.com` as a live mention of
# somebody who has nothing to do with the post.
MENTION_RE = re.compile(r"(?<![\w.-])@[\w-]+(?:\.[\w-]+)+")
TAG_RE = re.compile(r"(?<![\w#])#[^\d\s#][^\s#]*")

# A tag ends before its punctuation: `#atproto,` is the tag `atproto` followed
# by a comma, and a card that highlights the comma is showing a post that will
# not exist. Same for a sentence-final link. Bluesky trims both, so this does
# too — matching the greedy pattern is the easy half, agreeing with what gets
# published is the half that matters.
LINK_TRAIL = ".,;:!?"


def trim(kind: str, text: str) -> str:
    if kind == "tag":
        while text and unicodedata.category(text[-1]).startswith("P"):
            text = text[:-1]
        return text
    if kind == "link":
        text = text.rstrip(LINK_TRAIL)
        # A closing paren belongs to the URL only if the URL opened one —
        # "(see example.com/a_(b))" ends the link at the inner paren.
        while text.endswith(")") and text.count(")") > text.count("("):
            text = text[:-1].rstrip(LINK_TRAIL)
    return text


def facets(text: str) -> list[dict]:
    """Spans that will render as something other than plain text."""
    found = []
    for kind, pattern in (("mention", MENTION_RE), ("tag", TAG_RE), ("link", LINK_RE)):
        for m in pattern.finditer(text):
            span = trim(kind, m.group())
            if not span or span in ("#", "@"):
                continue
            start, end = m.start(), m.start() + len(span)
            # First match wins the span: a handle is a mention, not a domain.
            if any(f["start"] < end and start < f["end"] for f in found):
                continue
            found.append({"type": kind, "text": span, "start": start, "end": end})
    return sorted(found, key=lambda f: f["start"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, help="the draft post text")
    args = parser.parse_args()

    count = graphemes.count(args.text)
    marks = facets(args.text)

    print("Draft card shown in the chat, editable in place.")
    print(f"  {count}/{graphemes.LIMIT} graphemes"
          + (f" — {count - graphemes.LIMIT} OVER THE LIMIT, this cannot be posted "
             "as written. Shorten it and show the draft again."
             if count > graphemes.LIMIT else ""))
    for kind in ("link", "mention", "tag"):
        n = sum(1 for f in marks if f["type"] == kind)
        if n:
            print(f"  {n} {kind}{'s' if n > 1 else ''}: "
                  + ", ".join(f["text"] for f in marks if f["type"] == kind))

    print("\nThe draft is now on screen and can be edited there, so don't repeat "
          "the text back or describe what it says. Say only what is not on the "
          "card: why this post, and why framed this way.")

    render.emit(
        "draft",
        text=args.text,
        graphemes=count,
        limit=graphemes.LIMIT,
        facets=marks,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — the model needs the reason, not a trace
        print(f"Could not build the draft: {e}", file=sys.stderr)
        sys.exit(1)
