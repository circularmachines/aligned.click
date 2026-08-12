"""The CAUSE prototype — a web interface that runs the pipeline.

One page, two boxes (keywords, prompt notes), one play button. Play runs the
two-stage pipeline live:

1. **recall** — each keyword is searched on Bluesky through the tools
   (`tools/search_posts.py` -> the OAuth sidecar), giving candidates;
2. **precision** — `classify.py` applies the prompt notes with GreenPT v4
   flash and decides which candidates are worth surfacing.

The page shows the surfaced posts, each carrying the classifier's reason. That
reason is the seedling of the transparency label: the *why this surfaced*.

Storage is deliberately local and boring: a cause's keywords, notes and last
run append to `causes.json` next to this file. Nothing is written to atproto
yet — that decision stays in CAUSE.md for the real product.

Login is the sidecar's loopback flow re-grown here: this app offers its own
`/oauth/login` and `/oauth/callback` so a browser session lands on the
prototype instead of the production proxy. `start.sh` starts a dev-mode
sidecar that points its redirect at this port.

    python3 cause/app.py            # serves http://127.0.0.1:8780
"""

import datetime
import json
import os
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
REPO = ROOT.parent
TOOLS = REPO / "tools"

# The post cards on the page are `<atproto-post>` web components, vendored once
# for the chat and reader. This prototype serves the same file rather than
# copying it — one copy of a vendored bundle is the point.
SHARED = REPO / "reader" / "shared"
SHARED_FILES = {"atproto-wc.js", "theme.css"}

# The tools assume they are importable by bare name (they are run from
# tools/), so the simplest way to reuse them here is to put tools/ on the path
# and import them as the server/ directory already does.
sys.path.insert(0, str(TOOLS))

import classify  # noqa: E402

SIDECAR = os.environ.get("OAUTH_SIDECAR", "http://127.0.0.1:4098").rstrip("/")
PORT = int(os.environ.get("CAUSE_PORT", "8780"))
MAX_CANDIDATES = 40
MAX_KEYWORDS = 6
SEARCH_LIMIT_PER_TERM = 15

CAUSES_FILE = ROOT / "causes.json"


class CauseError(RuntimeError):
    """A user-facing failure (search, login, classification)."""


# --- sidecar -----------------------------------------------------------------


def sidecar_get(path: str) -> dict:
    url = f"{SIDECAR}/{path.lstrip('/')}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        raise CauseError(f"sidecar error ({e.code}): {e.read().decode('utf-8', 'replace')[:300]}") from None
    except OSError as e:
        raise CauseError(f"cannot reach the OAuth sidecar at {SIDECAR} ({e}). Is it running?") from None


def logged_in_did() -> str | None:
    """The active DID, or None. Prototype: the first logged-in account."""
    dids = sidecar_get("/oauth/sessions").get("dids", [])
    return dids[0] if dids else None


# --- the cause's items ------------------------------------------------------

# A keyword and a prompt note are each their own item, not words in one blob.
# The prototype stores them as independent objects because the real cause will
# store them as independent atproto records, from different authors: an item
# must be removable, attributable, and able to disagree with its siblings.


def item(text: str, author: str) -> dict:
    """One keyword or note as a first-class item. `author` is the DID who added
    it — the seed of the provenance label."""
    return {
        "id": uuid.uuid4().hex[:12],
        "text": text,
        "author": author,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"),
    }


def _split_keyword_items(text: str) -> list[str]:
    """The keywords box: one term per line or per comma. A multi-word term
    stays intact and is searched as an exact phrase."""
    raw = re.split(r"[\n,]+", text)
    return [t.strip() for t in raw if t.strip()][:MAX_KEYWORDS]


def _split_note_items(text: str) -> list[str]:
    """The notes box: each line is one note. A note is a discrete statement of
    judgment, so the line boundary is the item boundary."""
    return [n.strip() for n in text.splitlines() if n.strip()]


# --- recall ------------------------------------------------------------------


def recall(terms: list[str], did: str) -> list[dict]:
    """Keyword search on Bluesky, one term at a time, deduped by URI.

    Each term is searched separately and the results unioned: the causes model
    treats keywords as broad recall, where "any of these" is the request. (The
    tool's own all-terms-must-appear behaviour is exactly right for a single
    carefully chosen phrase and wrong for a list of alternates.)
    """
    os.environ["ACTING_DID"] = did

    from post_index import extract
    from search_posts import build_query, search_posts

    candidates: list[dict] = []
    seen: set[str] = set()
    for term in terms:
        query = build_query([term])
        for view in search_posts(query, SEARCH_LIMIT_PER_TERM):
            uri = view.get("uri")
            if uri in seen:
                continue
            seen.add(uri)
            candidates.append(extract(view))
            if len(candidates) >= MAX_CANDIDATES:
                return candidates
    return candidates


# --- storage -----------------------------------------------------------------


def save_run(did: str, keyword_items: list[dict], note_items: list[dict],
             surfaced: list[dict], candidates: int) -> None:
    record = {
        "created": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "did": did,
        "keywords": keyword_items,
        "notes": note_items,
        "candidate_count": candidates,
        "surfaced": [
            {"uri": s.get("uri"), "handle": s.get("handle"),
             "text": s.get("text"), "reason": s.get("reason"),
             "note_ids": s.get("note_ids")}
            for s in surfaced
        ],
    }
    runs = []
    if CAUSES_FILE.exists():
        try:
            runs = json.loads(CAUSES_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            runs = []
    runs.append(record)
    CAUSES_FILE.write_text(json.dumps(runs, ensure_ascii=False, indent=2))


# --- HTTP --------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "cause/0.1"

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("location", location)
        self.send_header("content-length", "0")
        self.end_headers()

    def _body(self) -> str:
        length = int(self.headers.get("content-length") or 0)
        return self.rfile.read(length).decode("utf-8") if length else ""

    # -- routes ------------------------------------------------------------

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            return self._page()
        if path == "/state":
            return self._state()
        if path == "/oauth/login":
            return self._login()
        if path == "/oauth/callback":
            return self._callback()
        if path.startswith("/shared/"):
            return self._shared(path[len("/shared/"):])
        if path == "/health":
            return self._json(200, {"ok": True})
        self._json(404, {"error": "no such route", "path": path})

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/run":
            return self._run()
        self._json(404, {"error": "no such route", "path": path})

    def _page(self) -> None:
        try:
            html = (ROOT / "index.html").read_text()
        except OSError as e:
            return self._send(500, f"cannot read index.html: {e}".encode(), "text/plain")
        self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _shared(self, name: str) -> None:
        """The vendored web components, from their single home in reader/."""
        if name not in SHARED_FILES:
            return self._json(404, {"error": "no such shared file"})
        try:
            body = (SHARED / name).read_bytes()
        except OSError as e:
            return self._send(500, str(e).encode(), "text/plain")
        ctype = "application/javascript; charset=utf-8" if name.endswith(".js") \
            else "text/css; charset=utf-8"
        self._send(200, body, ctype)

    def _state(self) -> None:
        try:
            did = logged_in_did()
            body = json.dumps(
                {"logged_in": bool(did), "did": did},
                ensure_ascii=False).encode()
            self._send(200, body)
        except CauseError as e:
            self._json(200, {"logged_in": False, "did": None, "note": str(e)})

    def _login(self) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        handle = (query.get("handle") or [""])[0].strip()
        if not handle:
            return self._json(400, {"error": "?handle= is required"})
        try:
            info = sidecar_get("/oauth/login?" + urllib.parse.urlencode({"handle": handle, "json": "1"}))
            return self._redirect(info["authorize"])
        except CauseError as e:
            self._json(502, {"error": str(e)})

    def _callback(self) -> None:
        """Finish the browser's login. The code exchange happens in the sidecar
        (it owns the DPoP key); this app only completes the round trip."""
        query = urllib.parse.urlparse(self.path).query
        try:
            info = sidecar_get("/oauth/callback?" + query)
        except CauseError as e:
            return self._json(502, {"error": str(e)})
        self._redirect("/")

    def _run(self) -> None:
        try:
            payload = json.loads(self._body() or "{}")
        except json.JSONDecodeError:
            return self._json(400, {"ok": False, "error": "body is not JSON"})

        keywords = str(payload.get("keywords", ""))
        notes = str(payload.get("notes", "")).strip()

        # Parse the body first so a malformed one fails before anything runs.
        if not keywords.strip() or not notes:
            return self._json(400, {"ok": False, "error": "Both keywords and prompt notes are required."})

        try:
            did = logged_in_did()
            if not did:
                return self._json(200, {"ok": False, "error": "login",
                                        "message": "Nobody is logged in. Log in with your Bluesky handle to search."})
            keyword_items = [item(t, did) for t in _split_keyword_items(keywords)]
            note_items = [item(t, did) for t in _split_note_items(notes)]
            terms = [k["text"] for k in keyword_items]
            if not terms:
                return self._json(400, {"ok": False, "error": "No searchable keywords in that box."})

            candidates = recall(terms, did)
            surfaced = classify.classify(candidates, [n["text"] for n in note_items]) \
                if candidates else []

            # Attribute each surfaced post to the note items it rests on. The
            # classifier cites notes by 1-based number; map those back to ids.
            for s in surfaced:
                refs = [note_items[i - 1] for i in s.get("note_inds", [])
                        if 0 < i <= len(note_items)]
                s["note_ids"] = [r["id"] for r in refs]
                s["note_texts"] = [r["text"] for r in refs]
                s.pop("note_inds", None)

            save_run(did, keyword_items, note_items, surfaced, len(candidates))
        except CauseError as e:
            return self._json(200, {"ok": False, "error": str(e)})
        except classify.ClassifyError as e:
            return self._json(200, {"ok": False, "error": str(e)})
        except Exception as e:  # noqa: BLE001 — surface anything, it is a prototype
            return self._json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

        return self._json(200, {
            "ok": True,
            "did": did,
            "keywords": keyword_items,
            "notes": note_items,
            "candidates": len(candidates),
            "surfaced": surfaced,
        })


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"CAUSE prototype on http://127.0.0.1:{PORT}  (sidecar {SIDECAR})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()