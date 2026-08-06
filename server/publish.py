"""Keep a conversation's atproto records in step with what happened and what
was chosen.

**A conversation nobody has published has no records at all.** No session, no
placeholder per turn, nothing: chatting here puts nothing on the network until
somebody presses publish.

This reverses an earlier stance — a record per turn from the moment it happened,
carrying words only by decision — and what that stance cost is worth naming,
because it is the reason for the reversal. A withheld record carries `createdAt`.
A repo full of them says when somebody chats, how often, and how long their
sessions run: a behavioural profile assembled from records containing no words,
for conversations they never chose to show anyone. Under that model there was no
changing your mind about having had the conversation, which is a strange promise
to attach to a tool for private exploration.

**Inside a published conversation every turn still gets a record**, carrying its
words only if they were chosen. This is where placeholders earn their keep, and
it is a different situation: published-by-selection alone gives a reader no way
to tell a continuous transcript from an edited one, so an answer to a question
that was held back reads as an answer to whatever came before it. Here the
withheld turn is a record in the right place with the right timestamp, and the
hole is the honest kind. The timing it discloses is about a conversation whose
author already decided to show part of it.

The two rules meet at zero, and `reconcile` follows them there: unticking the
last published turn takes the whole conversation down rather than leaving the
placeholders standing, because a hole is only honest when it is in something.

Publishing a turn is all-or-nothing except for one thing: **redaction**. A model
will state something about a named person that is wrong, and the choice between
publishing that and withholding the whole answer is a bad one — so a span can be
covered. The words never leave here; what goes on the network is a bar where
they were, so the reader sees that something was removed rather than reading a
seamlessly edited answer. Fixed-width, because a bar as wide as the words says
how long the name was.

One operation, `reconcile`, and it is idempotent: create what is missing, update
what changed, leave the rest. Called after a turn and again on every change of
mind, so a failed write is retried by the next call rather than needing its own
recovery path.
"""
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "publish"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import records as repo  # noqa: E402

SESSION_NSID = "click.aligned.chat.session"
MESSAGE_NSID = "click.aligned.chat.message"
STATE_FILE = Path(__file__).parent.parent / "private" / "published.json"

# What a redaction leaves in the text. Three full blocks whatever was removed:
# a bar the width of the words would leak their length, which is most of a name.
# Plain characters rather than a field of offsets, so a viewer that has never
# heard of this shows a redaction anyway instead of the words.
REDACTION_MARK = "█" * 3


class PublishError(RuntimeError):
    """A refusal safe to show the person who caused it."""


def _load() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.chmod(0o600)
    tmp.replace(STATE_FILE)


def when(ms: int | None) -> str:
    stamp = datetime.fromtimestamp((ms or 0) / 1000, timezone.utc)
    return stamp.isoformat(timespec="seconds").replace("+00:00", "Z")


# The same line tools/render.py emits. Reading it back rather than re-deriving
# which posts a turn was about means the record references exactly what was on
# screen, which is the only defensible definition of "about".
RENDER_RE = re.compile(r"^RENDER (\{.*\})$", re.M)


def shown(part: dict) -> tuple[list[str], list[str]]:
    """(post at-URIs, account DIDs) a render call put on screen.

    Guarded by kind, not by a field being present: a payload field means
    something only within its own kind, and reading `posts` off any payload has
    taken a turn down twice in this project.
    """
    state = part.get("state") or {}
    uris, dids = [], []
    for match in RENDER_RE.finditer(state.get("output") or ""):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if payload.get("kind") == "posts":
            uris += [p["uri"] for p in payload.get("posts") or [] if p.get("uri")]
        elif payload.get("kind") == "actor" and payload.get("did"):
            dids.append(payload["did"])
    return uris, dids


def summarize(part: dict) -> str:
    args = ((part.get("state") or {}).get("input")) or {}
    if not isinstance(args, dict):
        return ""
    pairs = [f"{k}={v}" for k, v in args.items()
             if isinstance(v, (str, int, float, bool)) and len(str(v)) < 80]
    return ", ".join(pairs)[:250]


def turns_from(messages: list[dict]) -> list[dict]:
    """opencode's message list as publishable turns, in order.

    Keeps the opencode message id: it is what a checkbox names, and what makes
    reconcile idempotent across calls.
    """
    out = []
    for message in messages:
        info = message.get("info") or {}
        role = info.get("role")
        if role not in ("user", "assistant"):
            continue
        text, steps, uris, dids = [], [], [], []
        for part in message.get("parts") or []:
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
            "id": info.get("id"),
            "role": role,
            "text": "\n\n".join(text),
            "createdAt": when((info.get("time") or {}).get("created")),
            "steps": steps,
            "uris": list(dict.fromkeys(uris)),
            "dids": list(dict.fromkeys(dids)),
        }
        if role == "assistant" and info.get("modelID"):
            turn["model"] = f"{info.get('providerID', '')}/{info['modelID']}".strip("/")
        out.append(turn)
    return out


def redact_text(text: str, spans: list[str] | None) -> tuple[str, list[str]]:
    """Text with every redacted span covered, and any span that is not in it.

    Every occurrence goes, not the one that was selected. Somebody redacting a
    name means the name, and a turn that repeats it would otherwise keep the
    copy nobody clicked on.

    A span that no longer matches is reported rather than skipped. Skipping it
    would publish the exact words somebody asked to remove, and do it silently —
    so the caller withholds the turn instead. The spans are checked against the
    turn when they are stored, and opencode's messages do not change afterwards,
    so this should never fire; it is here because of what it costs if it does.
    """
    missing = []
    for span in spans or []:
        if span and span in text:
            text = text.replace(span, REDACTION_MARK)
        else:
            missing.append(span)
    return text, missing


def build(turn: dict, session_uri: str, published: bool, refs: dict,
          made: list[str] | None = None, spans: list[str] | None = None) -> dict:
    """The record for one turn, in whichever of its two shapes applies.

    A withheld turn carries its role and its time and nothing else. Not the tool
    calls, not the posts it referenced — those are content, and "which accounts
    were you reading about" is exactly the sort of thing somebody would assume a
    withheld turn does not say.
    """
    record = {
        "$type": MESSAGE_NSID,
        "session": session_uri,
        "role": turn["role"],
        "createdAt": turn["createdAt"],
    }
    if not published:
        record["withheld"] = True
        record["text"] = ""
        return record

    text, missing = redact_text(turn["text"], spans)
    if missing:
        record["withheld"] = True
        record["text"] = ""
        return record

    record["text"] = text
    if turn.get("model"):
        record["model"] = turn["model"]
    if turn.get("steps"):
        record["steps"] = turn["steps"]
    # Posts the turn was about, and posts it produced. Both are strongRefs and
    # both are what the turn was, so they go in one list.
    wanted = list(dict.fromkeys(list(turn.get("uris", [])) + list(made or [])))
    pinned = [refs[u] for u in wanted if u in refs]
    if pinned:
        record["refs"] = pinned
    if turn.get("dids"):
        record["mentions"] = turn["dids"]
    return record


def inspect(session_id: str, turns: list[dict], did: str) -> dict:
    """What is on the network for this conversation, writing nothing.

    Opening an old conversation must not publish it. Reconciling on resume
    created a placeholder for every turn ever taken — a hundred records from one
    click, spending a third of an hour's rate limit, and putting the timing of
    conversations held long before any of this existed onto the network. Records
    exist because somebody pressed publish; looking is not that.

    Since a conversation with nothing published now has no records at all, this
    returns the empty answer for most of them, and returns it without a write.
    """
    entry = (_load().get(did) or {}).get(session_id) or {}
    return {
        "session": entry.get("session"),
        "turns": len(turns),
        "ids": [t["id"] for t in turns],
        "turns_meta": [{"id": t["id"], "role": t["role"]} for t in turns],
        "live": [mid for mid, m in (entry.get("messages") or {}).items()
                 if m.get("published")],
        "made": entry.get("made") or {},
        "redacted": entry.get("redacted") or {},
        "written": 0,
        "removed": 0,
        "failed": [],
        "published": sum(1 for m in (entry.get("messages") or {}).values()
                         if m.get("published")),
    }


def take_down(entry: dict, did: str) -> tuple[int, list[dict]]:
    """Remove this conversation's records, keeping what was chosen locally.

    The local entry survives with its `made` and `redacted` intact, so a
    conversation taken down and published again comes back with the same bars in
    the same places rather than quietly restoring words somebody covered.

    Each record is dropped from the entry only once its delete has landed, so a
    partial failure leaves the rest to the next call rather than orphaning
    records nothing here remembers. The session goes last and only if every
    message went: a session record with messages still pointing at it is a
    dangling reference, and the wrong half to lose first.
    """
    removed, failed = 0, []
    for mid, m in list((entry.get("messages") or {}).items()):
        try:
            repo.delete(MESSAGE_NSID, m["rkey"], did)
            entry["messages"].pop(mid)
            removed += 1
        except Exception as e:  # noqa: BLE001 — reported, never raised at the chat
            failed.append({"id": mid, "error": str(e)})
    if entry.get("session") and not entry.get("messages"):
        try:
            repo.delete(SESSION_NSID, entry["session"].rsplit("/", 1)[-1], did)
            entry.pop("session")
            removed += 1
        except Exception as e:  # noqa: BLE001
            failed.append({"id": "session", "error": str(e)})
    return removed, failed


def reconcile(session_id: str, turns: list[dict], selected: set[str], did: str) -> dict:
    """Bring the repo in line: a record per turn, published where chosen.

    `selected` holds the opencode message ids whose words should be public.
    Everything else gets — or keeps — a withheld record.

    With nothing selected there is nothing to be a record of. A conversation that
    has never been published stays absent, and one that was published is taken
    down — including its withheld turns, which is the part worth being deliberate
    about. They exist to mark the holes in something published, so when the last
    published turn goes they are not holes any more, only a list of times
    somebody spoke. Deleting them is the same act as unpublishing the words,
    carried to its end.
    """
    state = _load()
    entry = state.setdefault(did, {}).setdefault(session_id, {"messages": {}})

    if not selected:
        removed, failed = 0, []
        if entry.get("messages") or entry.get("session"):
            removed, failed = take_down(entry, did)
            _save(state)
        return {"session": entry.get("session"), "turns": len(turns),
                "published": 0, "written": 0, "removed": removed, "failed": failed}

    if not entry.get("session"):
        out = repo.create(SESSION_NSID, {
            "$type": SESSION_NSID,
            "createdAt": turns[0]["createdAt"] if turns else when(None),
        }, did)
        entry["session"] = out["uri"]
        _save(state)

    # Strong references only for turns actually being published — looking up
    # posts for withheld turns would be work done to throw away, and the lookup
    # itself is a read on somebody's behalf.
    made = entry.get("made") or {}
    wanted = list(dict.fromkeys(
        [u for t in turns if t["id"] in selected for u in t.get("uris", [])]
        + [u for t in turns if t["id"] in selected for u in made.get(t["id"], [])]))
    refs = repo.strong_refs(wanted, did) if wanted else {}

    redacted = entry.get("redacted") or {}
    written, failed = 0, []
    for turn in turns:
        published = turn["id"] in selected
        record = build(turn, entry["session"], published, refs,
                       made.get(turn["id"]), redacted.get(turn["id"]))
        known = entry["messages"].get(turn["id"])
        # Nothing to do if the record already says exactly this. Chatting makes
        # a lot of these calls and most are no-ops; a needless putRecord spends
        # rate-limit budget somebody would rather post with.
        #
        # Compared by content, not by the published flag. Comparing the flag
        # missed the case that matters: publish a conversation, then post from
        # it, and the reference to the new post is attached to a turn that was
        # already published — the flag has not changed, so nothing was written,
        # and the record kept the shape it had before the post existed. On the
        # reader that turn stayed a bare message with no card.
        fingerprint = hashlib.sha256(
            json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
        if known and known.get("sig") == fingerprint:
            continue
        try:
            if known:
                repo.put(MESSAGE_NSID, known["rkey"], record, did)
            else:
                out = repo.create(MESSAGE_NSID, record, did)
                known = {"rkey": out["uri"].rsplit("/", 1)[-1]}
                entry["messages"][turn["id"]] = known
            known["published"] = published
            known["sig"] = fingerprint
            written += 1
        except Exception as e:  # noqa: BLE001 — reported, never raised at the chat
            failed.append({"id": turn["id"], "error": str(e)})
    _save(state)

    return {
        "session": entry["session"],
        "turns": len(turns),
        "published": sum(1 for t in turns if t["id"] in selected),
        "written": written,
        "removed": 0,
        "failed": failed,
    }


def attach(session_id: str, message_id: str, uri: str, did: str) -> None:
    """Remember that a turn produced a post.

    A published turn shows posts by reference, and those references were only
    ever read off the cards tools drew — which made the record depend on a model
    choosing to call show-post. It did not always, and when it did not, the
    reader had a conversation with a hole where its result should be. Recording
    it here makes the reference a fact about what happened rather than a
    consequence of what was said about it.
    """
    state = _load()
    entry = state.setdefault(did, {}).setdefault(session_id, {"messages": {}})
    made = entry.setdefault("made", {})
    made.setdefault(message_id, [])
    if uri not in made[message_id]:
        made[message_id].append(uri)
    _save(state)


def redact(session_id: str, message_id: str, span: str, did: str,
           remove: bool = False) -> list[str]:
    """Cover a span of a turn's words, or uncover one. Returns what stands now.

    Kept here rather than in the record because this file is not published and
    the record is: the words being removed have to live somewhere to be removed
    from every future write of that turn, and `private/` is where the things
    nobody else sees already are.

    Uncovering is real — the span comes off the list and the next reconcile
    writes the words back. That is the honest behaviour for a control somebody
    might press by accident, and it is not a way to un-publish anything: a
    covered span was never on the network to begin with.
    """
    state = _load()
    entry = state.setdefault(did, {}).setdefault(session_id, {"messages": {}})
    spans = entry.setdefault("redacted", {}).setdefault(message_id, [])
    if remove:
        entry["redacted"][message_id] = spans = [s for s in spans if s != span]
        if not spans:
            entry["redacted"].pop(message_id, None)
    elif span not in spans:
        spans.append(span)
    _save(state)
    return spans


def made_in(session_id: str, did: str) -> dict[str, list[str]]:
    """{message id: posts that turn produced} — what the page redraws cards from."""
    return ((_load().get(did) or {}).get(session_id) or {}).get("made") or {}


def redactions_for(session_id: str, did: str) -> dict[str, list[str]]:
    """{message id: covered spans} — what the page needs to draw the bars."""
    return ((_load().get(did) or {}).get(session_id) or {}).get("redacted") or {}


def forget(session_id: str, did: str) -> dict:
    """Delete every record this conversation put on the network.

    Worth being exact about what this does. It removes them from the author's
    repo and emits deletes on the firehose; it does not reach anything that
    already mirrored, indexed or archived them. Publishing is not reversible,
    only retractable — so a published turn that somebody else copied stays
    copied, and this is still the right thing to do because the author's own
    copy is the only one they control.
    """
    state = _load()
    entry = ((state.get(did) or {}).get(session_id)) or {}
    removed, failed = 0, []
    for mid, m in (entry.get("messages") or {}).items():
        try:
            repo.delete(MESSAGE_NSID, m["rkey"], did)
            removed += 1
        except Exception as e:  # noqa: BLE001
            failed.append(str(e))
    if entry.get("session"):
        try:
            repo.delete(SESSION_NSID, entry["session"].rsplit("/", 1)[-1], did)
            removed += 1
        except Exception as e:  # noqa: BLE001
            failed.append(str(e))
    if did in state:
        state[did].pop(session_id, None)
        _save(state)
    return {"removed": removed, "failed": failed}


def status_all(did: str) -> dict[str, list[str]]:
    """{session id: message ids whose words are public} for one person."""
    return {sid: [mid for mid, m in (entry.get("messages") or {}).items()
                  if m.get("published")]
            for sid, entry in (_load().get(did) or {}).items()}


def status(session_id: str, did: str) -> dict:
    """What is on the network for this conversation already."""
    entry = (_load().get(did) or {}).get(session_id) or {}
    return {
        "session": entry.get("session"),
        "published": [mid for mid, m in (entry.get("messages") or {}).items()
                      if m.get("published")],
        "known": list((entry.get("messages") or {}).keys()),
    }
