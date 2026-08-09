#!/usr/bin/env python3
"""The collective's member list, kept on atproto rather than in a file.

The reader needs to know whose repos to render, and that list has to live
somewhere. It used to be `reader/authors.json`, which meant a member was not
rendered until somebody committed and pushed — and the obvious fix, having the
reader fetch it from the proxy, is the one thing `README.md` forbids: the
reader's whole claim is that a published conversation stays readable when this
machine is off, and an author list served from here would mean the mini-PC being
down renders nothing for anyone.

So the list goes where the conversations already are. One record per member in
the collective's own repo, read by the reader exactly as it reads everything
else — one more atproto fetch, no new dependency, and it survives this machine
being gone entirely.

**Written by the account that owns the authorising domain**, named by
`ADMIN_DID`, which logs into the sidecar like anybody else. There is no app
password for it and there should not be: a scoped session that can be revoked
beats a permanent credential that cannot, and the session already exists.

    python3 publish/members.py                 # list what is published
    python3 publish/members.py --add <did> [handle]
    python3 publish/members.py --remove <did>
    python3 publish/members.py --import        # from private/users.json, once
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import records  # noqa: E402

MEMBER_NSID = "click.aligned.chat.member"
ROOT = Path(__file__).parent.parent
USERS_FILE = ROOT / "private" / "users.json"
ENV_FILE = ROOT / ".env"


def admin_did() -> str:
    """Who writes the list. Read at call time, not at import.

    The proxy gets `.env` from systemd's EnvironmentFile, but `--approve` is run
    by hand from a shell that has not sourced anything — so the variable is
    there for the service and missing for the person. Falling back to reading
    `.env` is what `start.sh` already does for two other variables, and it means
    one implementation serves both callers.
    """
    did = os.environ.get("ADMIN_DID", "").strip()
    if not did and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("ADMIN_DID="):
                did = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not did:
        sys.exit("ADMIN_DID is not set — the member list is written by the account "
                 "owning the authorising domain, and this refuses to guess which "
                 "that is. Put it in .env, and make sure that account has logged "
                 "into the sidecar.")
    return did


_admin = admin_did  # the name the rest of this module was written against


def add(did: str, handle: str = "") -> None:
    """Admit somebody. Idempotent, because the key is the DID.

    putRecord rather than createRecord: there is no such thing as being a member
    twice, only a record that is newer. Re-running this on somebody already
    listed refreshes their handle and moves nothing else.
    """
    records.put(MEMBER_NSID, did, {
        "$type": MEMBER_NSID,
        "subject": did,
        **({"handle": handle} if handle else {}),
        "addedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, _admin())


def remove(did: str) -> None:
    """Stop rendering somebody. Their conversations are untouched.

    Worth being exact about what this is: it takes them off the list the reader
    walks, so their published records stop being *collected* here. It does not
    delete anything of theirs, and anyone who knows their handle can still read
    every record directly. Removing somebody from the collective and retracting
    what they published are different acts, and only they can do the second.
    """
    records.delete(MEMBER_NSID, did, _admin())


def published(did: str | None = None) -> list[dict]:
    """Every member record, read the way the reader reads it — unauthenticated.

    Deliberately not read back through the sidecar. This should answer the same
    thing a stranger with a browser would get, and going through our own
    authenticated path would hide exactly the failure worth catching: a record
    written but not actually visible.
    """
    repo = did or _admin()
    with urllib.request.urlopen(
            f"https://plc.directory/{urllib.parse.quote(repo)}", timeout=30) as r:
        doc = json.load(r)
    pds = next(s["serviceEndpoint"] for s in doc["service"]
               if s["type"] == "AtprotoPersonalDataServer")
    out, cursor = [], None
    while True:
        q = {"repo": repo, "collection": MEMBER_NSID, "limit": "100"}
        if cursor:
            q["cursor"] = cursor
        url = f"{pds}/xrpc/com.atproto.repo.listRecords?" + urllib.parse.urlencode(q)
        with urllib.request.urlopen(url, timeout=30) as r:
            page = json.load(r)
        out += page.get("records", [])
        cursor = page.get("cursor")
        if not cursor or not page.get("records"):
            return out


def main() -> None:
    argv = sys.argv[1:]
    if "--add" in argv:
        i = argv.index("--add")
        did = argv[i + 1] if i + 1 < len(argv) else sys.exit("--add needs a DID")
        handle = argv[i + 2] if i + 2 < len(argv) and not argv[i + 2].startswith("-") else ""
        add(did, handle)
        print(f"added {did}" + (f" (@{handle})" if handle else ""))
        return

    if "--remove" in argv:
        i = argv.index("--remove")
        did = argv[i + 1] if i + 1 < len(argv) else sys.exit("--remove needs a DID")
        remove(did)
        print(f"removed {did} — their published records are untouched")
        return

    if "--import" in argv:
        # One-off, for the move off reader/authors.json. The allowlist is the
        # thing that has always been true; this only mirrors it outward.
        users = json.loads(USERS_FILE.read_text() or "{}")
        if not users:
            sys.exit(f"no users in {USERS_FILE}")
        for did, info in users.items():
            add(did, info.get("handle", ""))
            print(f"  added {did} (@{info.get('handle', '')})")
        print(f"{len(users)} member(s) written")
        return

    found = published()
    if not found:
        print("no member records published yet — `--import` writes them from users.json")
        return
    print(f"{len(found)} member(s) in {_admin()}:")
    for rec in found:
        v = rec["value"]
        print(f"  {v.get('subject'):45} @{v.get('handle', '?'):<30} {v.get('addedAt', '')}")


if __name__ == "__main__":
    main()
