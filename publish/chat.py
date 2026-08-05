#!/usr/bin/env python3
"""Publish an opencode conversation to atproto as click.aligned.chat records.

Run by hand, and **`--dry-run` is not the flag, `--publish` is.** Everything
here is irreversible in the way that matters: a record is on the firehose the
moment it lands, and deleting it later removes your copy, not anyone else's.
Printing what would go out is the default because the interesting failure is
publishing something you had not read.

What gets published, and what deliberately does not:

- **The words.** Both roles. The assistant's text exists nowhere else, so it is
  stored rather than referenced.
- **The tool calls, by name.** The point of publishing a conversation with an
  agent is usually how it got there; a reply with the working removed is the
  least interesting part. Failed calls included — a workflow showing only the
  calls that worked is a misleading picture of working with an agent.
- **Not tool output.** Often large, often local paths, sometimes private data,
  and reproducible by anyone holding the same tools.
- **Not reasoning.** It is the model thinking out loud, not a claim it stands
  behind, and publishing it under someone's own identity misrepresents both.
- **Referenced posts as strong references**, never as copies. Pulled out of
  what the agent actually put on screen — the RENDER payloads — so the record
  says "this turn was about that post" with a CID pinning the version seen.

**Published as you, not as the project.** A conversation is somebody's speech,
so it lands in the repo of whoever was having it — the same account the agent
reads with. Only the lexicon schemas belong to the domain that authorises the
name; see publish/lexicons.py.

    python3 publish/chat.py --session ses_abc123
    python3 publish/chat.py --session ses_abc123 --title "Walking the graph" --publish
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import records  # noqa: E402
from bsky import acting_did, get  # noqa: E402

SERVER = "http://127.0.0.1:4096"
SESSION_NSID = "click.aligned.chat.session"
MESSAGE_NSID = "click.aligned.chat.message"

# The same line tools/render.py emits. Reading it here rather than re-deriving
# which posts a turn was about means the record references exactly what the
# reader saw, which is the only defensible definition of "about".
RENDER_RE = re.compile(r"^RENDER (\{.*\})$", re.M)
AT_URI_RE = re.compile(r"at://[a-zA-Z0-9:._%-]+/[a-zA-Z0-9.]+/[a-zA-Z0-9]+")


def fetch(path: str) -> list | dict:
    with urllib.request.urlopen(f"{SERVER}{path}", timeout=30) as r:
        return json.loads(r.read())


def when(ms: int | None) -> str:
    stamp = datetime.fromtimestamp((ms or 0) / 1000, timezone.utc)
    return stamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def summarize(part: dict) -> str:
    """One line on what a tool call was for, from its input."""
    state = part.get("state") or {}
    args = state.get("input") or {}
    if not isinstance(args, dict):
        return ""
    pairs = [f"{k}={v}" for k, v in args.items()
             if isinstance(v, (str, int, float, bool)) and len(str(v)) < 80]
    return ", ".join(pairs)[:250]


def shown(part: dict) -> tuple[list[str], list[str]]:
    """(post at-URIs, account DIDs) a render call put on screen.

    Two kinds of reference because they are two kinds of thing. A post is
    content, and the version matters — it gets a strongRef. A person is an
    identity, and the version does not: pinning a profile record would make a
    turn about someone go stale when they change their avatar, so an account is
    referenced by DID, which is also the discipline everything else here uses.
    """
    state = part.get("state") or {}
    uris, dids = [], []
    for match in RENDER_RE.finditer(state.get("output") or ""):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        # Guarded by kind, not by the field being present. A payload field means
        # something only within its own kind — reading `posts` off any payload
        # is what took a whole turn down in the UI, and it did it again here.
        if payload.get("kind") == "posts":
            for post in payload.get("posts") or []:
                if post.get("uri"):
                    uris.append(post["uri"])
        elif payload.get("kind") == "actor" and payload.get("did"):
            dids.append(payload["did"])
    return uris, dids


def turns(session_id: str) -> list[dict]:
    """The conversation as publishable turns, in order."""
    out = []
    for message in fetch(f"/session/{session_id}/message"):
        info = message.get("info", {})
        role = info.get("role")
        if role not in ("user", "assistant"):
            continue
        text, steps, uris, dids = [], [], [], []
        for part in message.get("parts", []):
            kind = part.get("type")
            if kind == "text" and (part.get("text") or "").strip():
                text.append(part["text"].strip())
            elif kind == "tool":
                state = part.get("state") or {}
                step = {"tool": part.get("tool") or "?"}
                if (line := summarize(part)):
                    step["summary"] = line
                if state.get("status") == "error":
                    step["failed"] = True
                steps.append(step)
                seen_uris, seen_dids = shown(part)
                uris += seen_uris
                dids += seen_dids
        if not text and not steps:
            continue  # a turn with nothing in it is not a turn
        turn = {
            "role": role,
            "text": "\n\n".join(text),
            "createdAt": when(info.get("time", {}).get("created")),
            "steps": steps,
            "uris": list(dict.fromkeys(uris)),
            "dids": list(dict.fromkeys(dids)),
        }
        if role == "assistant" and info.get("modelID"):
            turn["model"] = f"{info.get('providerID', '')}/{info['modelID']}".strip("/")
        out.append(turn)
    return out


def build(turn: dict, session_uri: str, refs: dict) -> dict:
    record = {
        "$type": MESSAGE_NSID,
        "session": session_uri,
        "role": turn["role"],
        "text": turn["text"],
        "createdAt": turn["createdAt"],
    }
    if turn.get("model"):
        record["model"] = turn["model"]
    if turn["steps"]:
        record["steps"] = turn["steps"]
    # Only URIs that still resolve: a strongRef needs a CID, and a post deleted
    # since the conversation has neither. Dropping it is the point — the record
    # is not a way to keep something its author took down.
    pinned = [refs[u] for u in turn["uris"] if u in refs]
    if pinned:
        record["refs"] = pinned
    if turn["dids"]:
        record["mentions"] = turn["dids"]
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--session", required=True, help="opencode session id")
    parser.add_argument("--title", help="what the conversation was about")
    parser.add_argument("--description", help="optional framing")
    parser.add_argument("--publish", action="store_true",
                        help="actually write to your repo — public and on the "
                             "firehose the moment it lands")
    args = parser.parse_args()

    conversation = turns(args.session)
    if not conversation:
        sys.exit(f"nothing publishable in {args.session}")

    wanted = list(dict.fromkeys(u for t in conversation for u in t["uris"]))
    refs = records.strong_refs(wanted) if wanted else {}

    did = acting_did()
    profile = get("app.bsky.actor.getProfile", {"actor": did})
    handle = profile.get("handle", did)
    print(f"{len(conversation)} turn(s) -> {handle} ({did}), "
          f"{sum(len(t['steps']) for t in conversation)} tool call(s), "
          f"{len(refs)}/{len(wanted)} referenced post(s) still resolvable, "
          f"{len({d for t in conversation for d in t['dids']})} account(s) mentioned")
    for turn in conversation:
        head = " ".join(turn["text"].split())[:88] or "(tool calls only)"
        tools = f"  [{', '.join(s['tool'] for s in turn['steps'])}]" if turn["steps"] else ""
        print(f"  {turn['role']:<9} {head}{tools}")

    if not args.publish:
        print("\nNothing written. Re-run with --publish to put this in your "
              "public repo, where it stays whether or not you delete it later.")
        return

    session = records.create(SESSION_NSID, {
        "$type": SESSION_NSID,
        **({"title": args.title} if args.title else {}),
        **({"description": args.description} if args.description else {}),
        "createdAt": conversation[0]["createdAt"],
    })
    print(f"\nsession  {session['uri']}")

    for turn in conversation:
        out = records.create(MESSAGE_NSID, build(turn, session["uri"], refs))
        print(f"  {turn['role']:<9} {out['uri']}")


if __name__ == "__main__":
    main()
