"""Shared Bluesky XRPC GET helper. Every read in tools/ goes through here.

**Nothing in this file handles a credential, and nothing in Python does.** The
call goes to the OAuth sidecar on loopback, naming the DID it should be made
as; the sidecar holds the session and signs the request. That is not a division
of labour we chose — atproto binds an access token to a key with DPoP and the
proof is signed per request, so the holder of the key has to be the caller.
There is no token that could be passed here.

What that removes is worth naming. There is no bearer token in an argv element,
no `-K -` config on stdin to keep it out of one, no cached session file, and no
app password. curl is gone too: it was here because Cloudflare rejects Python's
TLS, and this talks to 127.0.0.1.

**A read is made as somebody.** Not decoration: `searchPosts` returns 403 to an
anonymous caller and `getActorLikes` claims the profile does not exist, so the
two tools the agent reaches for most simply do not work without an identity.
Results are also viewer-scoped — blocks, mutes and moderation preferences apply
— so the answer genuinely depends on who is asking.

Failures are loud and never fall back to another identity. A sidecar that is
down is an error the caller sees. Quietly reading as the operator instead would
put someone else's name on what came back, and the person misled would be the
one it was attributed to.
"""
import http.client
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path



class BskyError(RuntimeError):
    """A failed Bluesky call. Its message is safe to print — it names a method
    and a reason, never a credential, because there is no longer a credential in
    this process to name.

    It lived in auth.py until app passwords did, and moved here when they went.
    Tools import it from this module.
    """


SIDECAR = os.environ.get("OAUTH_SIDECAR", "http://127.0.0.1:4098").rstrip("/")
TIMEOUT = 30


# Written by the auth proxy: which opencode session belongs to which person.
OWNERS_FILE = Path(__file__).parent.parent / "private" / "proxy-sessions.json"


def acting_did() -> str:
    """Whose identity this call is made as.

    **The session decides, not the environment.** opencode has no concept of a
    user, so a tool subprocess cannot ask who is chatting — but its wrapper is
    handed a `sessionID`, passes it down as `ACTING_SESSION`, and the proxy has
    already recorded who owns that session. So the DID is looked up per call
    from the login that caused it.

    That indirection is the whole of multi-user attribution. Reading a DID out
    of the environment instead would mean every tool ran as whoever started the
    server, no matter who was typing — invisible with one user, and with two it
    silently answers one person's question with another person's view of the
    network, blocks and mutes included.

    `ACTING_DID` remains as the fallback for running a tool by hand from a
    shell, where there is no session to belong to.
    """
    session = os.environ.get("ACTING_SESSION", "").strip()
    if session:
        try:
            owners = json.loads(OWNERS_FILE.read_text()).get("owners", {})
        except (OSError, json.JSONDecodeError):
            owners = {}
        did = owners.get(session)
        if not did:
            raise BskyError(
                f"session {session} has no owner on record, so there is nobody "
                "to read as. It was probably created before the proxy was, or "
                "outside it."
            )
        return _checked(did, "the session owner")

    did = os.environ.get("ACTING_DID", "").strip()
    if not did:
        raise BskyError(
            "No ACTING_SESSION and no ACTING_DID, so there is nobody to read "
            "as. Bluesky search and likes refuse anonymous callers. Log in at "
            f"`{SIDECAR}/oauth/login?handle=<your handle>`."
        )
    return _checked(did, "ACTING_DID")


def _checked(did: str, source: str) -> str:
    if not did.startswith("did:"):
        raise BskyError(f"{source} is {did!r}, which is a handle, not a DID — "
                        "a handle can move between accounts and a DID cannot.")
    return did


def get(method: str, params: dict, did: str | None = None) -> dict:
    qs = urllib.parse.urlencode({**params, "did": did or acting_did()}, doseq=True)
    url = f"{SIDECAR}/xrpc/{method}?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            body = response.read()
    except urllib.error.HTTPError as e:
        # The sidecar passes the upstream status and body through, so this is
        # usually Bluesky's own {error, message} — the useful text.
        detail = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(detail)
            detail = parsed.get("message") or parsed.get("error") or detail
        except json.JSONDecodeError:
            pass
        raise BskyError(f"{method}: {detail}") from None
    except (OSError, http.client.HTTPException) as e:
        # Not a Bluesky failure — the sidecar is unreachable. Say so plainly,
        # because the fix is to start a process, not to change the query.
        #
        # Deliberately wider than URLError, which only covers a connection that
        # fails to open. A sidecar that dies *mid-request* raises
        # RemoteDisconnected instead, and that escaped as a traceback until it
        # happened here — which is exactly the moment this has to be legible,
        # since a half-finished read is the one most likely to be mistaken for
        # an empty result.
        reason = getattr(e, "reason", None) or e
        raise BskyError(
            f"{method}: cannot reach the OAuth sidecar at {SIDECAR} ({reason}). "
            "Nothing can be read until it is running — start it with "
            "`node oauth/server.mjs`."
        ) from None

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise BskyError(f"{method}: unparseable response") from None
