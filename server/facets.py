"""Turn post text into atproto facets — the ranges that become links, mentions
and tags when the post is rendered.

**The offsets are UTF-8 byte indices, not character indices.** This is the part
that goes wrong, and it goes wrong invisibly: with plain ASCII the two are
identical, so a naive implementation passes every test until somebody writes an
em-dash or an emoji, and then every facet after it points at the wrong span. A
link becomes clickable two characters early and swallows the next word.

Bluesky's own rules, matched here rather than approximated:

- A **tag** ends before its trailing punctuation. `#atproto,` is the tag
  `atproto` followed by a comma.
- A **link** drops sentence-final punctuation, and a closing paren only belongs
  to it if the URL opened one.
- A **mention** must be preceded by a boundary, or `foo@bar.com` becomes a live
  mention of somebody with nothing to do with the post.
- A mention resolves to a **DID**. An unresolvable handle is not a mention at
  all — it is left as plain text, because a facet pointing at a DID that does
  not exist renders as a broken link forever.

Display-side detection lives in `tools/create_draft.py`, which draws the card.
This is the other half: what actually goes into the record.
"""
import re
import unicodedata

LINK_RE = re.compile(r"https?://\S+|(?<![\w@.])[\w-]+\.[a-z]{2,}(?:/\S*)?", re.I)
MENTION_RE = re.compile(r"(?<![\w.-])@([\w-]+(?:\.[\w-]+)+)")
TAG_RE = re.compile(r"(?<![\w#])#([^\d\s#][^\s#]*)")
LINK_TRAIL = ".,;:!?"

MENTION = "app.bsky.richtext.facet#mention"
LINK = "app.bsky.richtext.facet#link"
TAG = "app.bsky.richtext.facet#tag"


def _trim_link(text: str) -> str:
    text = text.rstrip(LINK_TRAIL)
    while text.endswith(")") and text.count(")") > text.count("("):
        text = text[:-1].rstrip(LINK_TRAIL)
    return text


def _trim_tag(text: str) -> str:
    while text and unicodedata.category(text[-1]).startswith("P"):
        text = text[:-1]
    return text


def build(text: str, resolve_handle) -> list[dict]:
    """Facets for `text`. `resolve_handle(handle) -> did | None` does the lookup.

    Overlaps are resolved first-match-wins in the order mention, tag, link, so a
    handle is a mention rather than a domain that happens to look like one.
    """
    raw = text.encode("utf-8")
    spans: list[tuple[int, int, dict]] = []

    def add(start: int, end: int, feature: dict) -> None:
        if any(s < end and start < e for s, e, _ in spans):
            return
        spans.append((start, end, feature))

    for m in MENTION_RE.finditer(text):
        did = resolve_handle(m.group(1))
        # No DID, no facet. The text stays, unlinked — which is honest, and
        # better than a mention nobody can follow.
        if did:
            add(m.start(), m.end(), {"$type": MENTION, "did": did})

    for m in TAG_RE.finditer(text):
        tag = _trim_tag(m.group(1))
        if tag:
            add(m.start(), m.start() + 1 + len(tag), {"$type": TAG, "tag": tag})

    for m in LINK_RE.finditer(text):
        url = _trim_link(m.group())
        if not url:
            continue
        full = url if url.startswith("http") else f"https://{url}"
        add(m.start(), m.start() + len(url), {"$type": LINK, "uri": full})

    out = []
    for start, end, feature in sorted(spans):
        out.append({
            "index": {
                # The conversion, and the only reason this module exists.
                "byteStart": len(text[:start].encode("utf-8")),
                "byteEnd": len(text[:end].encode("utf-8")),
            },
            "features": [feature],
        })

    # A facet whose bytes do not slice back to the text it claims is worse than
    # no facet: it renders as a link over the wrong words. Cheap to check, and
    # the failure it catches is the one this file exists to prevent.
    for facet in out:
        i = facet["index"]
        raw[i["byteStart"]:i["byteEnd"]].decode("utf-8")
    return out
