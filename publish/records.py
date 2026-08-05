#!/usr/bin/env python3
"""Writes records to a person's own atproto repo. The only write path here.

Everything under tools/ is a GET, deliberately: the agent reads Bluesky and
never changes it. This is the other side, and it lives outside tools/ for the
same reason — **there is no wrapper in .opencode/tools/ for any of it, so no
agent can call it.** Publishing is something a person does.

Custom records need no permission from anyone. `com.atproto.repo.createRecord`
takes any collection NSID and any JSON body; the PDS stores it, the relay puts
it on the firehose, and anything that cares can index it. The NSID's authority
must be a domain you control — it is the name's own segments reversed, minus
the last, so `click.aligned.chat.message` is authorised by `chat.aligned.click`
— because that is the only claim of ownership the protocol makes.

**Everything is written as a DID, through the OAuth sidecar.** There is no
account name to pass, no app password, and no token in this file: a write is
made by whoever logged in, using a session the sidecar holds. That matters more
here than it does for reads. A conversation is somebody's speech, so it goes in
their repo under their name — and the way to be sure a record carries the right
name is for the identity to be the argument rather than a default that can
quietly be wrong. A misattributed record is already on the firehose by the time
anyone notices.

What this does not get you is a reader. A custom record is durable, addressable
and public the moment it lands, and completely invisible until something knows
how to draw it.

That reader is a **separate project** — `aligned.click`, served as a static
page at read.aligned.click. Separate on purpose: it resolves handle → DID →
PDS → records itself and talks to nothing here, so a published conversation
stays readable when this machine is off. Anything that would make the reader
depend on this server takes that property away, and it is most of what makes
publishing to atproto worth doing.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from bsky import SIDECAR, BskyError, acting_did  # noqa: E402


def _call(method: str, body: dict, did: str) -> dict:
    """POST an XRPC procedure through the sidecar, as `did`."""
    request = urllib.request.Request(
        f"{SIDECAR}/xrpc/{method}?did={urllib.parse.quote(did)}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
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
        raise BskyError(f"{method}: {detail}") from None
    except (OSError, json.JSONDecodeError) as e:
        raise BskyError(
            f"{method}: cannot reach the OAuth sidecar at {SIDECAR} ({e}). "
            "Nothing can be published until it is running."
        ) from None



def create(collection: str, record: dict, did: str | None = None) -> dict:
    """Create one record under a generated TID key. Returns {uri, cid} — the
    strong reference to it.

    TID keys sort lexicographically by creation time, which is why nothing here
    carries a sequence number: the reading order is a property of the key.
    """
    repo = did or acting_did()
    out = _call("com.atproto.repo.createRecord", {
        "repo": repo,
        "collection": collection,
        "record": record,
    }, repo)
    return {"uri": out["uri"], "cid": out["cid"]}


def put(collection: str, rkey: str, record: dict, did: str | None = None) -> dict:
    """Write a record at a key you chose, creating or replacing it.

    For records whose key *is* their identity — a lexicon schema lives at its
    own NSID — where creating a second one is meaningless and updating in place
    is the only sensible operation.
    """
    repo = did or acting_did()
    out = _call("com.atproto.repo.putRecord", {
        "repo": repo,
        "collection": collection,
        "rkey": rkey,
        "record": record,
    }, repo)
    return {"uri": out["uri"], "cid": out["cid"]}


def delete(collection: str, rkey: str, did: str | None = None) -> None:
    """Remove a record from a repo.

    Worth being clear about what this does and does not do: it deletes that
    copy and emits a delete on the firehose. It does not reach anything that
    already mirrored, indexed or archived the record. Publishing is not
    reversible, only retractable.
    """
    repo = did or acting_did()
    _call("com.atproto.repo.deleteRecord",
          {"repo": repo, "collection": collection, "rkey": rkey}, repo)


def strong_refs(uris: list[str], did: str | None = None) -> dict[str, dict]:
    """{at-uri: {uri, cid}} for posts, so a reference can pin what was actually
    seen rather than whatever the post says later.

    A strongRef needs the CID, and an at-uri does not carry one, so it has to be
    looked up. Missing entries are posts that have been deleted since — dropped
    rather than referenced blindly, because a reference nobody can resolve is
    worse than no reference.

    The lookup is a read, and a read is made as somebody. `did` has to be
    passed by anything running server-side: the proxy deliberately carries no
    identity of its own, so falling through to the environment finds nothing
    and publishing fails at the one moment it has a post to pin — which is the
    only moment anybody notices.
    """
    from bsky import get  # a read: the one thing tools/ is for
    found = {}
    for i in range(0, len(uris), 25):  # getPosts takes 25 at a time
        data = get("app.bsky.feed.getPosts", {"uris": uris[i:i + 25]}, did)
        for post in data.get("posts", []):
            found[post["uri"]] = {"uri": post["uri"], "cid": post["cid"]}
    return found
