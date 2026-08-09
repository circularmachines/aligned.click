#!/usr/bin/env python3
"""Publish the lexicon schemas in lexicons/ to the authorising domain's repo.

A lexicon is only a claim until it is resolvable. Anyone can invent an NSID and
write records under it; what makes `click.aligned.chat.message` *mean*
something is that the schema for it can be found, by anyone, from the name
alone. That resolution is entirely decentralised and takes two things:

1. **The schema, published as a record** — collection
   `com.atproto.lexicon.schema`, record key the NSID itself. Written with
   putRecord rather than createRecord because the key is the identity: there is
   no such thing as a second copy of a schema, only a newer one.

**Who publishes it.** The account that owns the authorising domain, named by
`ADMIN_DID` — not whoever happens to be chatting. That account logs into the
OAuth sidecar like any other, which is a change from when it had an app
password: there are no app passwords here any more. It is also the only reason
that account ever needs to log in, so expect its session to have lapsed by the
time a schema next changes. Logging in again is one browser step, and is about
the right amount of friction for writing under the domain's own name.

2. **A DNS TXT record** at `_lexicon.aligned.click` whose value is
   `did=did:plc:...`, naming the repo above as the authority for every NSID
   under that domain. This script prints the exact line to add; it cannot set
   it for you, and until it exists the schemas are published but unfindable.

Publishing a schema is a promise, and a mild one: records already written
against an old version do not re-validate themselves. Lexicon evolution rules
are the usual ones — new optional fields are free, changing a type or making a
field required is not.

    python3 publish/lexicons.py
    python3 publish/lexicons.py --publish
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import records  # noqa: E402
from bsky import BskyError, admin_did  # noqa: E402

LEXICON_DIR = Path(__file__).parent.parent / "lexicons"
SCHEMA_NSID = "com.atproto.lexicon.schema"

# The account that owns the authorising domain, which is not whoever happens to
# be chatting. It has to have logged into the sidecar like anyone else — there
# is no app password for it any more — and that login is needed only when a
# schema changes, which should be close to never.
#
# Resolved in bsky.admin_did(), which also reads `.env`: this is run by hand
# from a shell, and only the service is handed that file by systemd.


def documents() -> list[tuple[str, dict]]:
    """(nsid, schema document) for every lexicon in the tree, checked."""
    out = []
    for path in sorted(LEXICON_DIR.rglob("*.json")):
        doc = json.loads(path.read_text())
        nsid = doc.get("id")
        if not nsid:
            sys.exit(f"{path}: no `id`, so there is no key to publish it under")
        # The file path mirrors the NSID by convention. If they disagree the
        # convention is broken somewhere, and the record would land under a name
        # nobody would think to look in.
        expected = LEXICON_DIR.joinpath(*nsid.split(".")).with_suffix(".json")
        if path != expected:
            sys.exit(f"{path}: id is {nsid}, which belongs at {expected}")
        out.append((nsid, doc))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--publish", action="store_true",
                        help="actually write the schemas to the repo")
    args = parser.parse_args()

    schemas = documents()
    try:
        did = admin_did()
    except BskyError as e:
        sys.exit(str(e))
    print(f"{len(schemas)} schema(s) -> {did}")
    for nsid, doc in schemas:
        authority = ".".join(reversed(nsid.split(".")[:-1]))
        print(f"  {nsid:<34} defs: {', '.join(doc['defs'])}   authority: {authority}")

    if not args.publish:
        print("\nNothing written. Re-run with --publish.")
        return

    for nsid, doc in schemas:
        # The whole document goes in, `id` included: the record key already says
        # the NSID, but a record that also states its own name is readable on its
        # own, and the schema record is deliberately an open object.
        out = records.put(SCHEMA_NSID, nsid, {"$type": SCHEMA_NSID, **doc}, did)
        print(f"  {out['uri']}")

    authorities = sorted({".".join(reversed(n.split(".")[:-1])) for n, _ in schemas})
    print("\nNow the half this cannot do for you — until these exist, the schemas "
          "are published but not resolvable:")
    for authority in authorities:
        print(f'  _lexicon.{authority}   TXT   "did={did}"')


if __name__ == "__main__":
    try:
        main()
    except BskyError as e:
        # A traceback here is noise: the interesting failure is almost always
        # "the domain account is not logged in", and that has a one-line fix.
        sys.exit(f"lexicon publish failed: {e}")
