"""Counting a Bluesky post the way Bluesky counts it.

The limit is **300 graphemes**, not characters and not bytes, and a draft over
it is simply not postable — so of everything a draft card shows, this is the
number that has to be right.

Three ways to get it wrong, all of which look fine in English:

- `len(text)` counts code points. "🇸🇪" is two, "👨‍👩‍👧‍👦" is seven, and an
  emoji with a skin tone is two. A post of family emoji would be rejected at
  what we told the creator was 43 characters.
- `len(text.encode())` counts bytes, which is the *other* atproto limit (3000)
  and roughly triple for the Swedish this product is mostly used on.
- Shortening URLs before counting. Bluesky's client displays a link truncated
  but the record keeps the whole thing, and the whole thing counts.

`regex` (with `\\X`) would do this properly and is not installed; the standard
library has no grapheme segmentation at all. So this is an approximation of
UAX #29 covering what actually appears in posts — combining marks, ZWJ
sequences, variation selectors, skin-tone modifiers and regional-indicator
pairs. It is exact for those and for all plain text. It does not implement
Hangul jamo composition or Indic conjunct clusters, which would undercount a
Korean or Devanagari draft; if this product ever writes in those, use `regex`.

The browser counts independently as the creator types — see the draft card in
index.html, which has `Intl.Segmenter` and so is exact.
"""
import unicodedata

ZWJ = "‍"
COMBINING = {"Mn", "Mc", "Me"}
VARIATION = range(0xFE00, 0xFE10)      # FE0F selects the emoji presentation
SKIN_TONE = range(0x1F3FB, 0x1F400)    # Fitzpatrick modifiers
REGIONAL = range(0x1F1E6, 0x1F200)     # two of these make one flag


def _joins(ch: str) -> bool:
    """True if `ch` attaches to the cluster before it rather than starting one."""
    cp = ord(ch)
    return (
        unicodedata.category(ch) in COMBINING
        or cp in VARIATION
        or cp in SKIN_TONE
    )


def count(text: str) -> int:
    """The number of graphemes in `text` — what Bluesky's 300 limit counts."""
    n = i = 0
    while i < len(text):
        n += 1
        prev_regional = ord(text[i]) in REGIONAL
        i += 1
        while i < len(text):
            ch = text[i]
            if ch == ZWJ:
                # A ZWJ and whatever it joins both belong to this cluster —
                # that is what makes 👨‍👩‍👧‍👦 one grapheme and not seven.
                i += 2
                prev_regional = False
                continue
            if _joins(ch):
                i += 1
                continue
            if ord(ch) in REGIONAL and prev_regional:
                i += 1  # flags pair up; a third indicator starts a new cluster
                prev_regional = False
                continue
            break
    return n


LIMIT = 300


def over(text: str) -> int:
    """How many graphemes past the limit, or 0. Never negative."""
    return max(0, count(text) - LIMIT)
