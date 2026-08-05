"""Writing to Bluesky: like, repost, reply, quote, post — and undoing them.

**A person does these, never the agent.** There is no wrapper in
`.opencode/tools/` for anything here and there must never be one. The agent
proposes; a human presses a button in their own session; the record goes to
their own repo with their own credentials. That is the same rule `publish/`
follows, for the same reason.

Everything is resolved here rather than trusted from the browser. The page sends
an at-uri and an action; this looks the post up, takes its CID fresh, works out
the thread root, and builds the record. The page cannot claim a CID, cannot
claim a root, and cannot post as anyone but whoever the cookie says it is.

Two details that are easy to get wrong and are not obvious from the outside:

- **A reply needs a root and a parent.** Replying to a reply means inheriting
  its root, not pointing both at the post you clicked. Getting this wrong does
  not error — it silently starts a second thread that nobody sees.
- **A like is a record, so undoing one is deleting that record**, by its rkey.
  There is no unlike call.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import facets as facets_mod  # noqa: E402
import graphemes  # noqa: E402

SIDECAR = "http://127.0.0.1:4098"
POST = "app.bsky.feed.post"
LIKE = "app.bsky.feed.like"
REPOST = "app.bsky.feed.repost"
FOLLOW = "app.bsky.graph.follow"


class ActionError(RuntimeError):
    """A refusal safe to show the person who caused it."""


def _xrpc(method: str, did: str, params: dict | None = None, body: dict | None = None) -> dict:
    query = urllib.parse.urlencode({**(params or {}), "did": did}, doseq=True)
    url = f"{SIDECAR}/xrpc/{method}?{query}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message") or detail
        except json.JSONDecodeError:
            pass
        raise ActionError(detail) from None
    except OSError as e:
        raise ActionError(f"the OAuth sidecar is not reachable ({e})") from None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _post_view(uri: str, did: str) -> dict:
    data = _xrpc("app.bsky.feed.getPosts", did, {"uris": [uri]})
    posts = data.get("posts") or []
    if not posts:
        raise ActionError("that post no longer exists — it may have been deleted")
    return posts[0]


def _ref(post: dict) -> dict:
    return {"uri": post["uri"], "cid": post["cid"]}


def _text_record(did: str, text: str) -> dict:
    text = text.strip()
    if not text:
        raise ActionError("nothing to post")
    count = graphemes.count(text)
    if count > graphemes.LIMIT:
        raise ActionError(f"{count} characters, {count - graphemes.LIMIT} over the "
                          f"{graphemes.LIMIT} limit — shorten it first")

    def resolve(handle: str) -> str | None:
        try:
            return _xrpc("com.atproto.identity.resolveHandle", did, {"handle": handle}).get("did")
        except ActionError:
            return None

    record = {"$type": POST, "text": text, "createdAt": now()}
    if (marks := facets_mod.build(text, resolve)):
        record["facets"] = marks
    return record


def _create(collection: str, record: dict, did: str) -> dict:
    out = _xrpc("com.atproto.repo.createRecord", did,
                body={"repo": did, "collection": collection, "record": record})
    return {"uri": out["uri"], "cid": out["cid"]}


def state(uri: str, did: str) -> dict:
    """What this person has already done to a post, and its current counts.

    The viewer half matters more than it looks. Without it the Like button
    starts unpressed on a post you already liked, and pressing it writes a
    *second* like record — atproto will happily store both, and the only way
    back is deleting them one at a time. The counts are here too so the card can
    be drawn from one call rather than two.
    """
    post = _post_view(uri, did)
    viewer = post.get("viewer") or {}
    return {
        "like": viewer.get("like"),
        "repost": viewer.get("repost"),
        "counts": {
            "likes": post.get("likeCount", 0),
            "replies": post.get("replyCount", 0),
            "reposts": post.get("repostCount", 0),
            "quotes": post.get("quoteCount", 0),
        },
    }


def actor_state(actor: str, did: str) -> dict:
    """Whether this person already follows an account.

    The same trap as likes, and worse to get wrong: a Follow button that starts
    blank on somebody you already follow writes a second follow record when
    pressed. Bluesky shows one relationship either way, so nothing looks amiss
    — you just have two records, and unfollowing removes one of them.
    """
    profile = _xrpc("app.bsky.actor.getProfile", did, {"actor": actor})
    viewer = profile.get("viewer") or {}
    return {
        "handle": profile.get("handle"),
        "did": profile.get("did"),
        "following": viewer.get("following"),
        "followedBy": viewer.get("followedBy"),
    }


def follow(actor: str, did: str) -> dict:
    """Follow an account. The subject is a DID, not a strongRef — a person is
    not a version of their profile, so there is nothing to pin."""
    profile = _xrpc("app.bsky.actor.getProfile", did, {"actor": actor})
    subject = profile.get("did")
    if not subject:
        raise ActionError(f"no account {actor!r}")
    if subject == did:
        raise ActionError("you cannot follow yourself")
    return _create(FOLLOW, {"$type": FOLLOW, "subject": subject, "createdAt": now()}, did)


def like(uri: str, did: str) -> dict:
    post = _post_view(uri, did)
    return _create(LIKE, {"$type": LIKE, "subject": _ref(post), "createdAt": now()}, did)


def repost(uri: str, did: str) -> dict:
    post = _post_view(uri, did)
    return _create(REPOST, {"$type": REPOST, "subject": _ref(post), "createdAt": now()}, did)


def reply(uri: str, text: str, did: str) -> dict:
    parent = _post_view(uri, did)
    # Inherit the thread's root. A reply to a reply that names itself as root
    # starts a second thread, silently — no error, just a conversation nobody
    # else can see in context.
    existing = (parent.get("record") or {}).get("reply") or {}
    root = existing.get("root") or _ref(parent)
    record = _text_record(did, text)
    record["reply"] = {"root": {"uri": root["uri"], "cid": root["cid"]}, "parent": _ref(parent)}
    return _create(POST, record, did)


def quote(uri: str, text: str, did: str) -> dict:
    post = _post_view(uri, did)
    record = _text_record(did, text)
    record["embed"] = {"$type": "app.bsky.embed.record", "record": _ref(post)}
    return _create(POST, record, did)


# What a backlink shows. The URL it points at is ~100 characters — a third of a
# post — but a facet is a byte range with a `uri` attached, and the range does
# not have to contain the URL. So the post costs this many characters and links
# to the long one.
BACKLINK_TEXT = "read.aligned.click"


def post(text: str, did: str, link: dict | None = None) -> dict:
    """Post. With `link`, append a short label pointing at a longer URL.

    The facet is built here rather than by the detector, which would see
    "read.aligned.click" and link it to the bare domain — the right-looking
    wrong answer, landing on the reader's front page instead of the turn that
    produced this.
    """
    record = _text_record(did, text)
    if not link:
        return _create(POST, record, did)

    suffix = f"\n\n{BACKLINK_TEXT}"
    combined = record["text"] + suffix
    if graphemes.count(combined) > graphemes.LIMIT:
        raise ActionError(
            f"{graphemes.count(combined)} characters with the backlink, over the "
            f"{graphemes.LIMIT} limit. Shorten the post, or post it without one.")
    raw = record["text"].encode("utf-8")
    start = len(raw) + len("\n\n".encode("utf-8"))
    record["text"] = combined
    record.setdefault("facets", []).append({
        "index": {"byteStart": start, "byteEnd": start + len(BACKLINK_TEXT.encode("utf-8"))},
        "features": [{"$type": facets_mod.LINK, "uri": link["uri"]}],
    })
    return _create(POST, record, did)


def undo(uri: str, did: str) -> dict:
    """Delete one of your own records — the only way to unlike or unrepost.

    The repo is taken from the URI and checked against the caller rather than
    trusted, so a browser cannot ask to delete out of somebody else's repo.
    """
    parts = uri.removeprefix("at://").split("/")
    if len(parts) != 3:
        raise ActionError("not a record uri")
    repo, collection, rkey = parts
    if repo != did:
        raise ActionError("that record is not yours")
    if collection not in (LIKE, REPOST, POST, FOLLOW):
        raise ActionError(f"{collection} is not something this can delete")
    _xrpc("com.atproto.repo.deleteRecord", did,
          body={"repo": did, "collection": collection, "rkey": rkey})
    return {"deleted": uri}


ACTIONS = {
    "like": lambda p, did: like(p["uri"], did),
    "repost": lambda p, did: repost(p["uri"], did),
    "reply": lambda p, did: reply(p["uri"], p.get("text", ""), did),
    "quote": lambda p, did: quote(p["uri"], p.get("text", ""), did),
    "post": lambda p, did: post(p.get("text", ""), did, p.get("link")),
    "undo": lambda p, did: undo(p["uri"], did),
    "state": lambda p, did: state(p["uri"], did),
    "follow": lambda p, did: follow(p["actor"], did),
    "actor-state": lambda p, did: actor_state(p["actor"], did),
}


def perform(payload: dict, did: str) -> dict:
    action = payload.get("action")
    handler = ACTIONS.get(action)
    if not handler:
        raise ActionError(f"no such action: {action!r}")
    if action in ("follow", "actor-state"):
        if not payload.get("actor"):
            raise ActionError("actor is required")
    elif action != "post" and not payload.get("uri"):
        raise ActionError("uri is required")
    return handler(payload, did)
