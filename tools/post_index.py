"""Assigns small stable integers to at:// URIs so the model can refer to a
post as `[3]` instead of repeating the raw URI. Indices only ever grow, so
the same post always gets the same index and the browser UI (which watches
tool output over SSE) can rebuild the same index -> uri mapping independently.

Also the single place where a Bluesky postView is turned into the one-line
text the model reads — so search/author/thread all surface the same metadata
(timestamp, engagement counts, and any images/video/link/quote).
"""
import json
import re
from pathlib import Path

INDEX_FILE = Path(__file__).parent / ".post_index.jsonl"


def _load() -> dict[str, int]:
    existing: dict[str, int] = {}
    if INDEX_FILE.exists():
        for line in INDEX_FILE.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            existing[entry["uri"]] = entry["index"]
    return existing


def resolve(indices: list[int]) -> dict[int, str]:
    """The reverse direction: `3` -> `at://…`, for indices that exist.

    Assignment is append-only and never reused, so an index handed out in an
    earlier session still resolves — which is what lets `show-post` take the
    same `[N]` the model already saw instead of a URI it would have to copy.
    """
    by_index = {index: uri for uri, index in _load().items()}
    return {i: by_index[i] for i in indices if i in by_index}


def assign_indices(uris: list[str]) -> dict[str, int]:
    existing = _load()
    next_index = max(existing.values(), default=0) + 1
    result: dict[str, int] = {}
    new_lines = []
    for uri in uris:
        if uri in existing:
            result[uri] = existing[uri]
            continue
        result[uri] = next_index
        new_lines.append(json.dumps({"index": next_index, "uri": uri}))
        next_index += 1

    if new_lines:
        with INDEX_FILE.open("a") as f:
            for line in new_lines:
                f.write(line + "\n")
    return result


def _fmt_date(iso: str) -> str:
    """'2026-07-20T14:03:22.123Z' -> '2026-07-20 14:03' (UTC, to the minute)."""
    if not iso:
        return "?"
    return iso.replace("T", " ")[:16]


def _domain(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url).split("/")[0] if url else ""


def _media_markers(embed: dict) -> list[str]:
    """One or more short tags describing an embed's media, e.g. ['images:2']."""
    etype = embed.get("$type", "")
    if "embed.images" in etype:
        imgs = embed.get("images", [])
        alt = sum(1 for i in imgs if (i.get("alt") or "").strip())
        tag = f"images:{len(imgs)}"
        return [tag + f" ({alt} w/alt)" if alt else tag]
    if "embed.video" in etype:
        return ["video"]
    if "embed.external" in etype:
        dom = _domain((embed.get("external") or {}).get("uri", ""))
        return [f"link:{dom}" if dom else "link"]
    return []


def summarize_embed(post: dict) -> list[str]:
    """Turn a postView's hydrated embed into tags: images / video / link / quote."""
    embed = post.get("embed") or {}
    etype = embed.get("$type", "")
    if "recordWithMedia" in etype:
        return _media_markers(embed.get("media") or {}) + ["quote"]
    if "embed.record" in etype:  # a bare quote post
        return ["quote"]
    return _media_markers(embed)


def extract(post: dict) -> dict:
    """Normalize a raw Bluesky postView into the fields we print/store."""
    author = post.get("author") or {}
    record = post.get("record") or {}
    return {
        "uri": post["uri"],
        "did": author.get("did", ""),
        "handle": author.get("handle", ""),
        "displayName": author.get("displayName", ""),
        "text": record.get("text", ""),
        "createdAt": record.get("createdAt", ""),
        "likeCount": post.get("likeCount", 0),
        "replyCount": post.get("replyCount", 0),
        "repostCount": post.get("repostCount", 0),
        "media": summarize_embed(post),
    }


def format_line(index: int, p: dict, prefix: str = "") -> str:
    """The one canonical post line the model reads. `p` is an extract() dict.

    `[N] @handle  <date>  L likes / R replies / P reposts [media]  at://uri — preview`
    """
    preview = " ".join(p["text"].split())[:140]
    counts = f"{p['likeCount']} likes / {p['replyCount']} replies / {p['repostCount']} reposts"
    media = f"  [{', '.join(p['media'])}]" if p["media"] else ""
    return (
        f"{prefix}[{index}] @{p['handle']}  {_fmt_date(p['createdAt'])}  "
        f"{counts}{media}  {p['uri']} — {preview}"
    )


def print_indexed(posts: list[dict], empty: str = "(no posts)") -> None:
    """Print one enriched line per raw postView. Reply with just `[N]` to show
    a post — never repeat the at:// URI yourself; the browser UI embeds it from
    this line automatically.

    An empty result must say so out loud. Printing nothing gives the model no
    way to tell "no matches" from "the tool broke", and it will guess: in
    ses_06231e268ffegDJX4Kwbai40lr six searches returned zero characters and
    the agent burned six more calls groping for terms that would work.
    """
    if not posts:
        print(empty)
        return
    rows = [extract(p) for p in posts]
    indices = assign_indices([r["uri"] for r in rows])
    for r in rows:
        print(format_line(indices[r["uri"]], r))
