"""Read-only Bluesky access with an app password, for the index crawler.

The production product bans app passwords on purpose: a server holding a
credential is a server that can be robbed, and every tool call is made as the
person who logged in. This experiment is different in two explicit ways:
the crawler is the operator's *own* account, and it runs read-only searches in
the background. An app password is scoped per tool and revocable at any time —
an app password removed from Bluesky is a crawler that stops, not a crawler
that breaks.

The sidecar alternative kept breaking: the same session store is shared by the
loopback and production clients, and a session written by one is refused by the
other (`private_key_jwt required a client_assertion`). This exists to sidestep
that, not to be the product's future.

Only search is used here. Nothing this module does writes anything.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://bsky.social/xrpc"
ENV_FILE = Path(__file__).parent.parent / ".env"


class BskySearchError(RuntimeError):
    """A failed call against the public API. The message is safe to print."""


class AuthError(BskySearchError):
    """App-password login refused — the credentials in .env are wrong."""


def credentials() -> tuple[str, str]:
    """(handle, app password) from the environment or .env. Blank if unset."""
    def _read(key: str) -> str:
        value = os.environ.get(key, "").strip()
        if value:
            return value
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""

    return _read("INDEX_BLUESKY_HANDLE"), _read("INDEX_BLUESKY_APP_PASSWORD")


def configured() -> bool:
    h, p = credentials()
    return bool(h and p)


_session: dict | None = None


def session() -> dict:
    """A live createSession result, created once and reused. Refused if 401."""
    global _session
    if _session:
        return _session
    handle, app_password = credentials()
    if not handle or not app_password:
        raise AuthError(
            "INDEX_BLUESKY_HANDLE / INDEX_BLUESKY_APP_PASSWORD are not set "
            "in .env — the crawler has no search account.")
    body = json.dumps({"identifier": handle, "password": app_password}).encode()
    req = urllib.request.Request(
        f"{BASE}/com.atproto.server.createSession", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            _session = json.loads(r.read())
            return _session
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise AuthError(f"createSession failed ({e.code}): {detail[:200]}") from None
    except OSError as e:
        raise BskySearchError(f"cannot reach bsky.social ({e})") from None


def xrpc_get(nsid: str, params: dict) -> dict:
    """An authenticated GET. A 401 drops the cached session and retries once."""
    sess = session()
    url = f"{BASE}/{nsid}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {sess['accessJwt']}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            global _session
            _session = None
            session()
            return xrpc_get(nsid, params)
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message") or detail
        except json.JSONDecodeError:
            pass
        raise BskySearchError(f"{nsid}: {detail}") from None
    except OSError as e:
        raise BskySearchError(f"cannot reach bsky.social ({e})") from None