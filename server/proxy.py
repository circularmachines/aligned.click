#!/usr/bin/env python3
"""The auth proxy: the only thing that is ever exposed, and the only thing that
knows who anyone is.

Everything else on this machine binds 127.0.0.1 — opencode, the OAuth sidecar,
the static files. This sits in front, decides whether a request has a logged-in
person behind it, and refuses it if not.

Three jobs, in order of how badly each fails:

1. **Authenticate.** A cookie names a session, a session names a DID, and a DID
   is either on the invite list or is not. Everything below assumes this
   happened.

2. **Enforce session ownership.** opencode has no concept of a user: its
   sessions are global to the process, so `/session/<id>/…` for somebody else's
   id would just work. The proxy owns the map from opencode session to DID, and
   that map is the whole of multi-user isolation.

3. **Filter the event stream.** This is the one that would go wrong quietly.
   `GET /event` is a *single global SSE stream* — verified, not assumed: a
   client with no filter sees sessions created by other requests, and the
   deltas carrying their message text. The browser already drops foreign
   events, but that is cosmetic; by then the words have arrived. So events are
   filtered here, and filtered **fail-closed**: an event whose session cannot
   be established as yours is dropped, not forwarded.

What it deliberately does not do: hold a Bluesky credential. Login is the
sidecar's, and the cookie here is ours — a random token that means "this
browser is that DID", nothing more.

    python3 server/proxy.py            # serve
    python3 server/proxy.py --users    # who may log in
"""
import base64
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import actions  # noqa: E402
import models as catalog  # noqa: E402
import publish  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import post_index  # noqa: E402

ROOT = Path(__file__).parent.parent
PUBLIC = ROOT / "public"
# The reader is a sibling site in this repo, deployed to GitHub Pages from
# `reader/`. `reader/shared/` is what the two have in common, and it sits
# inside the deployed directory because Pages can only publish one tree.
SHARED = ROOT / "reader" / "shared"
OPENCODE_CONFIG = ROOT / "agent" / "opencode.json"
PRIVATE = ROOT / "private"

PORT = int(os.environ.get("PROXY_PORT", 8778))
OPENCODE = os.environ.get("OPENCODE_URL", "http://127.0.0.1:4096").rstrip("/")
# opencode's own server password. A second lock, behind this one — it knows
# nothing about users and cannot enforce session ownership, so it is not a
# substitute for anything here. What it buys is that a mistake in this file's
# routing does not immediately expose an unauthenticated agent, and that
# anything else on the machine cannot simply talk to opencode.
#
# HTTP Basic, and the username is literally `opencode` — measured, not guessed:
# an empty username, `admin` and a random one all return 401 with the right
# password.
OPENCODE_PASSWORD = os.environ.get("OPENCODE_SERVER_PASSWORD", "")
OPENCODE_AUTH = (
    "Basic " + base64.b64encode(f"opencode:{OPENCODE_PASSWORD}".encode()).decode()
    if OPENCODE_PASSWORD else None
)
SIDECAR = os.environ.get("OAUTH_SIDECAR", "http://127.0.0.1:4098").rstrip("/")
# Set once the tunnel exists. Its presence also means "we are on https", which
# is what makes the cookie Secure.
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
# Where a published conversation can be read. A separate host on purpose: it
# talks to nothing here, so a post that links back stays readable when this
# machine is off.
READER = os.environ.get("READER_URL", "https://read.aligned.click").rstrip("/")

USERS_FILE = PRIVATE / "users.json"
WAITLIST_FILE = PRIVATE / "waitlist.json"
# Optional. Point it at ntfy.sh, a Discord webhook, anything that takes a POST —
# a waitlist nobody is told about is a file that fills up quietly.
WAITLIST_WEBHOOK = os.environ.get("WAITLIST_WEBHOOK", "")
SESSIONS_FILE = PRIVATE / "proxy-sessions.json"
COOKIE = "aligned_session"
SESSION_TTL = 30 * 24 * 3600

# Per-DID limits. Not for abuse — for the loop. Every turn bills to one GreenPT
# key, and an agent that gets stuck is the normal way that becomes expensive.
RATE_PER_MINUTE = int(os.environ.get("RATE_PER_MINUTE", 120))
PROMPTS_PER_DAY = int(os.environ.get("PROMPTS_PER_DAY", 300))

# Events with no session of their own that are still safe to forward. Anything
# not listed and not owned is dropped: a stream is the wrong place to guess.
GLOBAL_EVENTS = {"server.connected"}

# What the pages may load and where they may talk to.
#
# `script-src 'self'` is the one doing the work. This page can post, publish and
# redact as whoever is logged in, and until 2026-08-05 it pulled marked,
# DOMPurify and atproto-wc from a CDN at unpinned URLs — so whatever that CDN
# served on any given load ran with those powers. The libraries are in
# `reader/shared/` now and nothing may be fetched from anywhere else, even if a
# tag for it reappears.
#
# `'unsafe-inline'` is there because the whole application is one inline script
# and one inline style; it is not what this policy is for. `connect-src 'self'`
# is: an injected script still could not send anything off this origin.
CSP = ("default-src 'none'; "
       "script-src 'self' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: https:; "
       "connect-src 'self' https://public.api.bsky.app https://plc.directory; "
       "font-src 'self'; "
       "base-uri 'none'; "
       "form-action 'self'; "
       "frame-ancestors 'none'")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json",
    ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
}


def mtime(path):
    try:
        return path.stat().st_mtime
    except OSError:
        return 0


def load(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.chmod(0o600)
    tmp.replace(path)


class State:
    """Who may log in, who is logged in, and which opencode session is whose.

    Held in memory and written through to disk, because a proxy restart that
    logged everybody out would be a restart nobody wants to do.
    """

    def __init__(self):
        # {did: {"handle": str, "added": iso}} — hand-edited. Invite-only means
        # a file somebody has to type into, not a signup form.
        self.users = load(USERS_FILE, {})
        self.users_mtime = mtime(USERS_FILE)
        # People who signed in and were not on the list. Keyed by DID, which is
        # the point of recording them here rather than taking a form: they
        # proved they hold the handle, so approving one is a copy, not a
        # judgement about whether the name is real.
        self.waiting = load(WAITLIST_FILE, {})
        blob = load(SESSIONS_FILE, {})
        self.cookies = blob.get("cookies", {})   # token -> {did, created}
        self.owners = blob.get("owners", {})     # opencode session id -> did
        self.hits = defaultdict(deque)           # did -> request times
        self.prompts = defaultdict(deque)        # did -> prompt times

    def persist(self):
        save(SESSIONS_FILE, {"cookies": self.cookies, "owners": self.owners})

    def refresh_users(self):
        """Re-read the allowlist if it changed on disk.

        Approving somebody should let them in, not let them in after a restart —
        and the same applies in the other direction, which matters more: taking
        a line out of users.json has to end that person's access now. Cheap: one
        stat per request, and a read only when the file actually moved.
        """
        current = mtime(USERS_FILE)
        if current != self.users_mtime:
            self.users = load(USERS_FILE, self.users)
            self.users_mtime = current

    def allowed(self, did, field):
        """What this person may choose for `field` — None meaning no limit.

        An optional list on their line in users.json:

            "did:plc:…": {"handle": "…", "models": ["greenpt/glm-5.2"],
                          "tools": ["search-posts", "show-post"]}

        Absent means everything the server offers, so nobody's access changes by
        adding the feature. Present means exactly that list and nothing else.

        Read through `self.users`, which is re-read when the file moves — so
        narrowing somebody takes effect on their next request, the same as
        removing them does. That is the property that makes this usable: it is
        an allowlist you can edit while people are connected.
        """
        entry = self.users.get(did) or {}
        listed = entry.get(field)
        return set(listed) if isinstance(listed, list) else None

    def user_for(self, token):
        entry = self.cookies.get(token or "")
        if not entry:
            return None
        if time.time() - entry["created"] > SESSION_TTL:
            self.cookies.pop(token, None)
            self.persist()
            return None
        # Re-checked on every request, not just at login: removing someone from
        # users.json has to end their access now, not when their cookie lapses.
        if entry["did"] not in self.users:
            return None
        return entry["did"]

    def wait(self, did, handle):
        """Record an access request. Returns True if this is a new one."""
        if did in self.waiting:
            return False
        self.waiting[did] = {
            "handle": handle,
            "requested": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        save(WAITLIST_FILE, self.waiting)
        return True

    def login(self, did):
        token = secrets.token_urlsafe(32)
        self.cookies[token] = {"did": did, "created": time.time()}
        self.persist()
        return token

    def own(self, session_id, did):
        self.owners[session_id] = did
        self.persist()

    def owns(self, session_id, did):
        return self.owners.get(session_id) == did

    def within_limits(self, did, is_prompt):
        now = time.time()
        recent = self.hits[did]
        recent.append(now)
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) > RATE_PER_MINUTE:
            return "too many requests — slow down"
        if is_prompt:
            day = self.prompts[did]
            day.append(now)
            while day and now - day[0] > 86400:
                day.popleft()
            if len(day) > PROMPTS_PER_DAY:
                return f"daily limit of {PROMPTS_PER_DAY} messages reached"
        return None


state = State()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "aligned-proxy"
    _body = None

    # ---- plumbing -------------------------------------------------------

    def reply(self, status, body=b"", content_type="application/json", extra=None):
        # Drain the request body before answering, always.
        #
        # This is not tidiness. On a keep-alive connection, a body left unread
        # stays in the socket, and the *next* request on that connection starts
        # parsing partway through it — observed here as
        # `Unsupported method '{"action":"like",…}GET'`. A refusal that returns
        # early is exactly the case where the body goes unread, so every
        # rejected POST desynchronises the connection it arrived on, and a body
        # chosen to look like a request would be read as one.
        self.body_bytes()
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}):
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def cookie_token(self):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE:
                return value
        return None

    def set_cookie(self, token):
        # Host-only: no Domain attribute, deliberately. read.aligned.click is a
        # sibling subdomain served by GitHub Pages, so a cookie scoped to
        # .aligned.click would be sent to GitHub on every reader page load.
        bits = [f"{COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Lax",
                f"Max-Age={SESSION_TTL}"]
        if PUBLIC_URL.startswith("https://"):
            bits.append("Secure")
        return ("Set-Cookie", "; ".join(bits))

    def upstream_headers(self):
        headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
        if OPENCODE_AUTH:
            headers["Authorization"] = OPENCODE_AUTH
        return headers

    def body_bytes(self):
        """The request body, read at most once and remembered.

        Cached because it must also be *drained* on paths that never look at
        it — see `reply`. Reading twice would return empty the second time and
        silently turn a real body into no body.
        """
        if self._body is None:
            length = int(self.headers.get("Content-Length") or 0)
            self._body = self.rfile.read(length) if length else b""
        return self._body

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    # ---- routing --------------------------------------------------------

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_DELETE(self):
        self.route("DELETE")

    def do_HEAD(self):
        # `reply` already omits the body for HEAD. Without this, health checks
        # and anything that probes before fetching get a 501, which reads like
        # the service is broken rather than uninterested.
        self.route("GET")

    def route(self, method):
        # One handler instance serves every request on a keep-alive connection,
        # so this cache has to be cleared per request. Leaving it set meant the
        # second POST on a connection got the first one's body back and never
        # read its own — which left those bytes in the socket and desynchronised
        # the third request. The same failure as before, one level further in.
        self._body = None
        # Every request, not only the authenticated ones. Hanging this off
        # user_for() meant the public routes never checked, so what the process
        # believed about membership depended on which URL was asked for.
        state.refresh_users()
        url = urllib.parse.urlsplit(self.path)
        path = url.path

        # Public, and necessarily so: the authorization server fetches these
        # itself, with no cookie and no browser involved.
        if path in ("/client-metadata.json", "/jwks.json"):
            return self.pass_to_sidecar(path)
        if path == "/healthz":
            return self.reply(200, {"ok": True, "users": len(state.users)})
        # The components both sites share. GitHub Pages serves the same bytes to
        # the world, so gating them here would only mean the login page could
        # not use the colours the rest of it does.
        if path.startswith("/shared/"):
            return self.serve_static(path)
        if path == "/login":
            return self.begin_login(url)
        if path == "/oauth/callback":
            return self.finish_login(url)
        if path == "/logout":
            return self.logout()

        did = state.user_for(self.cookie_token())
        if not did:
            if path.startswith("/session") or path in ("/event", "/action", "/me", "/model", "/setup", "/publish", "/redact", "/sessions"):
                return self.reply(401, {"error": "not logged in"})
            return self.reply(302, b"", "text/plain", [("Location", "/login")])

        limited = state.within_limits(did, path.endswith("/prompt_async"))
        if limited:
            return self.reply(429, {"error": limited})

        if path == "/me":
            return self.whoami(did)
        if path == "/model":
            # What is actually running, asked of opencode rather than read from
            # a file that says what somebody meant to run.
            try:
                cfg = self.from_opencode("/config")
            except OSError as e:
                return self.reply(502, {"error": str(e)})
            return self.reply(200, {"model": cfg.get("model")})
        if path == "/setup":
            return self.list_setup(did)
        if path == "/publish":
            return self.publish_session(did)
        if path == "/redact":
            return self.redact_turn(did)
        if path == "/sessions":
            return self.list_sessions(did)
        if path == "/action":
            return self.perform_action(did)
        if path == "/event":
            return self.stream_events(did)
        if method == "DELETE" and path.startswith("/session/"):
            return self.delete_session(path.split("/")[2], did)
        if path.startswith("/session"):
            return self.pass_to_opencode(method, url, did)
        return self.serve_static(path)

    # ---- login ----------------------------------------------------------

    def begin_login(self, url):
        handle = urllib.parse.parse_qs(url.query).get("handle", [""])[0].strip()
        if not handle:
            return self.reply(200, LOGIN_PAGE, "text/html; charset=utf-8")
        try:
            out = self.ask_sidecar(f"/oauth/login?handle={urllib.parse.quote(handle)}&json=1")
        except OSError as e:
            return self.reply(502, {"error": f"OAuth sidecar unreachable: {e}"})
        if "authorize" not in out:
            return self.reply(400, out)
        return self.reply(302, b"", "text/plain", [("Location", out["authorize"])])

    def finish_login(self, url):
        try:
            out = self.ask_sidecar(f"/oauth/callback?{url.query}")
        except OSError as e:
            return self.reply(502, {"error": f"OAuth sidecar unreachable: {e}"})
        did = out.get("did")
        if not did:
            return self.reply(400, out)
        if did not in state.users:
            # Authenticated, and not on the list. This is the request: they have
            # just proved they hold the handle, so the waitlist entry is a
            # verified identity rather than something somebody typed. It still
            # grants nothing — an allowlist that grows by being visited is not
            # an allowlist.
            handle = self.handle_for(did)
            if state.wait(did, handle):
                notify_waitlist(did, handle)
            # replace(), not format(): these templates carry a stylesheet, and
            # `:root{color-scheme:…}` is a perfectly good format field as far as
            # str.format is concerned. It raised KeyError on the one path that
            # only runs for somebody who is not yet a user — so it worked for
            # everyone who could already log in.
            page = (WAITING.replace("{did}", did)
                           .replace("{handle}", handle))
            return self.reply(200, page, "text/html; charset=utf-8")
        token = state.login(did)
        return self.reply(302, b"", "text/plain",
                          [("Location", "/"), self.set_cookie(token)])

    def logout(self):
        token = self.cookie_token()
        if token:
            state.cookies.pop(token, None)
            state.persist()
        return self.reply(302, b"", "text/plain", [
            ("Location", "/login"),
            ("Set-Cookie", f"{COOKIE}=; Path=/; HttpOnly; Max-Age=0"),
        ])

    def handle_for(self, did):
        """The handle behind a DID, for the waitlist to be readable. Falls back
        to the DID: a request recorded under an unreadable name is still a
        request, and losing it would be worse."""
        try:
            out = self.ask_sidecar(
                f"/xrpc/app.bsky.actor.getProfile?did={urllib.parse.quote(did)}"
                f"&actor={urllib.parse.quote(did)}")
            return out.get("handle") or did
        except (OSError, ValueError):
            return did

    def ask_sidecar(self, path):
        with urllib.request.urlopen(f"{SIDECAR}{path}", timeout=30) as r:
            return json.loads(r.read())

    def pass_to_sidecar(self, path):
        try:
            with urllib.request.urlopen(f"{SIDECAR}{path}", timeout=15) as r:
                return self.reply(200, r.read(), r.headers.get("content-type", "application/json"))
        except urllib.error.HTTPError as e:
            return self.reply(e.code, e.read(), "application/json")
        except OSError as e:
            return self.reply(502, {"error": f"OAuth sidecar unreachable: {e}"})

    def delete_session(self, session_id, did):
        """Remove a conversation: its records first, then the conversation.

        That order matters. The records are found through the map this proxy
        keeps, so dropping the conversation first would leave records on the
        network with nothing left that knows they exist — public, undeletable
        by any normal path, and belonging to a conversation the author believes
        they deleted.
        """
        if not state.owns(session_id, did):
            return self.reply(404, {"error": "no such session"})
        try:
            gone = publish.forget(session_id, did)
        except Exception as e:  # noqa: BLE001
            return self.reply(502, {"error": f"could not remove records: {e}"})

        request = urllib.request.Request(f"{OPENCODE}/session/{session_id}",
                                         headers=self.upstream_headers(), method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=60) as r:
                r.read()
        except urllib.error.HTTPError as e:
            return self.reply(e.code, {"error": e.read().decode("utf-8", "replace")[:200],
                                       "recordsRemoved": gone["removed"]})
        except OSError as e:
            return self.reply(502, {"error": f"opencode unreachable: {e}",
                                    "recordsRemoved": gone["removed"]})

        state.owners.pop(session_id, None)
        state.persist()
        return self.reply(200, {"deleted": session_id, **gone})

    @staticmethod
    def untouched(session):
        """A session nothing ever happened in.

        Opening the page creates one, so most of them are page loads rather than
        conversations. `created == updated` with no tokens spent means nothing
        was ever written to it — and a session where a message was sent but no
        reply came back does not match, which is right: that is a turn, and it
        is the kind somebody might want to look at again.
        """
        t = session.get("time") or {}
        tokens = session.get("tokens") or {}
        return (t.get("created") == t.get("updated")
                and not any(v for k, v in tokens.items() if isinstance(v, int)))

    def list_sessions(self, did):
        """The conversations this person owns, newest first.

        Filtered against the proxy's own ownership map rather than asking
        opencode, which holds everybody's and knows nothing about users. A
        conversation nobody claims is not shown to anyone.

        Empty ones are removed as we go rather than listed. They accumulate one
        per page load, so leaving them turns the list into a thing you have to
        search — and a list of forty things you did not do makes the two you did
        harder to find.
        """
        try:
            raw = self.from_opencode("/session")
        except OSError as e:
            return self.reply(502, {"error": f"opencode unreachable: {e}"})
        keep = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("keep", [""])[0]
        published = publish.status_all(did)
        mine, swept = [], 0
        for s in raw:
            if not state.owns(s.get("id"), did):
                continue
            # Never the one they are sitting in: it is empty because they have
            # not typed yet.
            if s["id"] != keep and self.untouched(s) and not published.get(s["id"]):
                if self.drop_session(s["id"]):
                    swept += 1
                    continue
            times = s.get("time") or {}
            mine.append({
                "id": s["id"],
                "title": s.get("title") or "(untitled)",
                "created": times.get("created"),
                "updated": times.get("updated"),
                "published": len(published.get(s["id"], [])),
            })
        mine.sort(key=lambda x: x.get("updated") or 0, reverse=True)
        return self.reply(200, {"sessions": mine, "swept": swept})

    def drop_session(self, session_id):
        """Delete one session from opencode and forget we owned it."""
        request = urllib.request.Request(f"{OPENCODE}/session/{session_id}",
                                         headers=self.upstream_headers(), method="DELETE")
        try:
            with urllib.request.urlopen(request, timeout=30) as r:
                r.read()
        except OSError:
            return False
        state.owners.pop(session_id, None)
        state.persist()
        return True

    def enabled_tools(self):
        """Tool names `opencode.json` switches on — the ceiling for everyone.

        Read here rather than asked of opencode, because this is the config's
        own statement of what the agent may do. `"*": false` with a list of
        exceptions is how it is written, so the exceptions are the answer.
        """
        try:
            configured = (json.loads(OPENCODE_CONFIG.read_text()).get("tools") or {})
        except (OSError, json.JSONDecodeError):
            return []
        return sorted(name for name, on in configured.items() if on and name != "*")

    def agents_for(self, did):
        """Agents this person may name, the default one first.

        An agent is a named bundle of tools and permissions — which is what
        makes it the only mechanism that can offer `bash` to one person and not
        another. A prompt carries a model, a tool list and an agent, but never
        a permission, so permission is set per agent in `opencode.json` and the
        gate is here: who is allowed to name which.

        Nobody may name one unless their line in users.json says so. That is
        also the fix for a hole that was already open — `?product=<name>` put a
        name straight into the prompt body, so any user could ask for any agent
        including one that can run commands.
        """
        try:
            defined = json.loads(OPENCODE_CONFIG.read_text()).get("agent") or {}
        except (OSError, json.JSONDecodeError):
            defined = {}
        allowed = state.allowed(did, "agents") or set()
        out = [{"id": "", "name": "Reader",
                "description": (defined.get("build") or {}).get("description", "")}]
        for name, spec in defined.items():
            if name == "build" or name not in allowed:
                continue
            out.append({"id": name, "name": name,
                        "description": spec.get("description", "")})
        return out

    def list_setup(self, did):
        """What this person may choose, and what runs when they choose nothing.

        Models come from `models/` — the same files `server/models.py` reads, so
        a new model is added in one place and appears here without anyone
        editing the page. Models that cannot call tools are listed too, and
        marked: leaving them out invites the question of where they went, and
        the answer is worth showing rather than hiding.

        Both lists are then cut to this person's allowance. What is not offered
        here is also refused on the way in — this decides what the page draws,
        never what the server permits.
        """
        try:
            described = catalog.described()
        except (OSError, json.JSONDecodeError) as e:
            return self.reply(500, {"error": f"could not read models/: {e}"})
        try:
            default = self.from_opencode("/config").get("model")
        except OSError:
            default = None

        may_use = state.allowed(did, "models")
        models = []
        for mid, m in described.items():
            ident = f"{catalog.PROVIDER}/{mid}"
            if may_use is not None and ident not in may_use:
                continue
            models.append({
                "id": ident,
                "name": m.get("name") or mid,
                "tools": m.get("tools"),
                "usable": m.get("tools") in catalog.USABLE,
            })
        if may_use is not None and default not in may_use:
            default = next((m["id"] for m in models if m["usable"]), None)
        return self.reply(200, {
            "default": default,
            "models": models,
            "agents": self.agents_for(did),
        })

    def tools_for(self, did):
        """Tools this person may call: the config's list, cut to their allowance."""
        enabled = self.enabled_tools()
        may_use = state.allowed(did, "tools")
        return [t for t in enabled if may_use is None or t in may_use]

    def with_checked_prompt(self, body, did, impose_tools=True):
        """The prompt body, with the model checked and the tools imposed.

        Two different jobs, because the two fields fail in opposite directions.

        A **model** is refused. The page can ask for any provider and model it
        likes, and a model that cannot call tools does not fail in a way anyone
        would notice — there is no error, the agent answers with tool markup in
        its prose, reads its own malformed output back and answers again,
        burning a turn of somebody's energy each time (see `server/models.py`).
        So it is checked against the files that say what each model does, and
        anything undescribed, unusable or not on this person's list is refused
        rather than tried. That also keeps the provider from being swapped for
        one whose key we hold and whose bill we would pay.

        **Tools** cannot be refused the same way, because *absence* is what
        grants them: a name the body never mentions runs under `opencode.json`,
        which switches it on. So a restriction has to be written in rather than
        checked — every tool this person may not call is set to false here,
        whatever the page did or did not send. The page can narrow further; it
        cannot widen, and it cannot widen by staying silent either.
        """
        if not body:
            body = b"{}"
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return body, None   # not ours to parse; opencode will judge it
        if not isinstance(payload, dict):
            return body, None

        if "model" in payload:
            choice = payload.get("model") or {}
            provider, model = choice.get("providerID"), choice.get("modelID")
            if provider != catalog.PROVIDER:
                return body, f"{provider} is not a provider this server runs"
            described = catalog.described().get(model)
            if not described:
                return body, (f"no models/{model}.json — a model has to be described "
                              f"before it can be selected")
            if described.get("tools") not in catalog.USABLE:
                return body, (f"{model} cannot call tools ({described.get('tools')}), "
                              f"and this agent is nothing but tools")
            may_use = state.allowed(did, "models")
            if may_use is not None and f"{provider}/{model}" not in may_use:
                return body, f"{model} is not one of the models on your account"

        if payload.get("agent"):
            named = payload["agent"]
            if named not in {a["id"] for a in self.agents_for(did) if a["id"]}:
                return body, f"{named} is not an agent on your account"

        # Session creation takes a `permission` block, which would set the
        # session's own rules and outrank the agent's. Nothing here sends one,
        # and a browser that did would be writing the very policy this file
        # exists to apply.
        payload.pop("permission", None)

        if not impose_tools:
            return json.dumps(payload).encode(), None

        asked = payload.get("tools")
        tools = dict(asked) if isinstance(asked, dict) else {}
        mine = set(self.tools_for(did))
        for name in self.enabled_tools():
            if name not in mine:
                tools[name] = False
        # Anything switched on that this person may not call goes off. Reached
        # only by a request that did not come from the page, which is exactly
        # the case worth covering.
        for name, on in list(tools.items()):
            if on and name not in mine:
                tools[name] = False
        payload["tools"] = tools
        return json.dumps(payload).encode(), None

    def publish_session(self, did):
        """Bring a conversation's records in line with what was chosen.

        The session must be one of theirs — the same check every other
        /session route makes, and for the same reason: without it a request
        could publish somebody else's conversation into its own repo.
        """
        if self.command != "POST":
            return self.reply(405, {"error": "POST only"})
        try:
            payload = json.loads(self.body_bytes() or b"{}")
        except json.JSONDecodeError:
            return self.reply(400, {"error": "body is not JSON"})

        session_id = payload.get("session")
        if not session_id or not state.owns(session_id, did):
            return self.reply(404, {"error": "no such session"})

        try:
            raw = self.from_opencode(f"/session/{session_id}/message")
        except OSError as e:
            return self.reply(502, {"error": f"opencode unreachable: {e}"})

        turns = publish.turns_from(raw)
        try:
            if payload.get("inspect"):
                out = publish.inspect(session_id, turns, did)
            else:
                out = publish.reconcile(
                    session_id, turns, set(payload.get("publish") or []), did)
        except Exception as e:  # noqa: BLE001
            return self.reply(502, {"error": str(e)})
        # The turn list goes back so the page can draw a box per turn without
        # having to agree separately with the server about what a turn is.
        out["ids"] = [t["id"] for t in turns]
        out["turns_meta"] = [{"id": t["id"], "role": t["role"]} for t in turns]
        # Which turns' words are already public. The page needs this to come
        # back to a conversation with the boxes as they were left rather than as
        # if nothing had ever been published.
        out["live"] = publish.status(session_id, did)["published"]
        out["redacted"] = publish.redactions_for(session_id, did)
        # On both paths, not just inspect: a page that took `made` from a
        # reconcile reply used to get nothing back and forget every card the
        # conversation had produced.
        out.setdefault("made", publish.made_in(session_id, did))
        return self.reply(200, out)

    def redact_turn(self, did):
        """Cover part of a turn's words — and take them out of the record now.

        The page sends the words to remove, not the text to publish. That is the
        whole of the trust boundary here: a page that could send replacement text
        could put sentences in the model's mouth and publish them under its
        label, which is the one thing a record of a conversation must not allow.
        Sending a span to delete can only ever remove.

        The span is checked against what the model actually said, and a span
        that is not there is refused rather than stored. A stored redaction that
        matches nothing is a redaction that silently does not happen.

        If the conversation is already published this rewrites it immediately.
        Redaction is nearly always a reaction to seeing something in public, so
        waiting for a separate press would leave it up for as long as it took to
        find the button.
        """
        if self.command != "POST":
            return self.reply(405, {"error": "POST only"})
        try:
            payload = json.loads(self.body_bytes() or b"{}")
        except json.JSONDecodeError:
            return self.reply(400, {"error": "body is not JSON"})

        session_id = payload.get("session")
        if not session_id or not state.owns(session_id, did):
            return self.reply(404, {"error": "no such session"})
        message_id = payload.get("message")
        span = payload.get("text") or ""
        remove = bool(payload.get("remove"))
        if not message_id or not span.strip():
            return self.reply(400, {"error": "message and text are required"})
        span = span.strip()

        try:
            raw = self.from_opencode(f"/session/{session_id}/message")
        except OSError as e:
            return self.reply(502, {"error": f"opencode unreachable: {e}"})

        turns = publish.turns_from(raw)
        turn = next((t for t in turns if t["id"] == message_id), None)
        if not turn:
            return self.reply(404, {"error": "that turn is not in this conversation"})
        if not remove and span not in turn["text"]:
            return self.reply(400, {"error": "those words are not in that turn — "
                                             "select them again"})

        spans = publish.redact(session_id, message_id, span, did, remove)

        # Only if it is out already. Redacting a turn nobody has published must
        # not be what publishes it.
        written, failed = 0, []
        already = set(publish.status(session_id, did)["published"])
        if already:
            try:
                out = publish.reconcile(session_id, turns, already, did)
                written, failed = out["written"], out["failed"]
            except Exception as e:  # noqa: BLE001
                return self.reply(502, {"error": f"covered, but the record was "
                                                 f"not rewritten: {e}"})
        return self.reply(200, {"spans": spans, "written": written, "failed": failed,
                                "redacted": publish.redactions_for(session_id, did)})

    def record_action(self, payload, out, did):
        """Put what just happened into the conversation, and into the record.

        Both halves are done here rather than asked of the model. The message
        goes in with `noReply`, so it costs no turn and cannot be ignored; the
        post is attached to it as a reference, so a published conversation shows
        the post whether or not anything ever drew a card for it.

        This used to depend on the agent calling show-post when told. It
        sometimes did not — and a missing card meant a missing reference, so the
        published conversation had a hole exactly where its result belonged.
        """
        session_id = (payload.get("origin") or {}).get("session")
        if not session_id or not state.owns(session_id, did):
            return {}

        verb = {"post": "posted that draft",
                "reply": "replied to that post",
                "quote": "quoted that post"}[payload["action"]]
        said = (payload.get("text") or "").strip()
        message_id = "msg_" + secrets.token_hex(12)
        body = json.dumps({
            "messageID": message_id,
            "noReply": True,
            "parts": [{"type": "text",
                       "text": f"I {verb} — it is [{out['index']}].\n\n{said}"}],
        }).encode()
        request = urllib.request.Request(
            f"{OPENCODE}/session/{session_id}/message",
            data=body, headers=self.upstream_headers(), method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as r:
                r.read()
        except OSError as e:
            # The post is out; this is bookkeeping. Say so rather than failing
            # an action that already succeeded.
            return {"noted": False, "noteError": str(e)}

        publish.attach(session_id, message_id, out["uri"], did)

        # If they are already publishing this conversation, publish this turn
        # too. Otherwise pressing Post after pressing Publish leaves the record
        # ending just before its result: a conversation that proposed a post,
        # with no sign the post was made.
        #
        # It is not a new disclosure. The turn says what they posted, and they
        # posted it — the words are public already, under their name, by their
        # own press. A conversation nobody has published stays unpublished.
        already = publish.status(session_id, did)["published"]
        if already:
            try:
                raw = self.from_opencode(f"/session/{session_id}/message")
                turns = publish.turns_from(raw)
                publish.reconcile(session_id, turns,
                                  set(already) | {message_id}, did)
            except Exception as e:  # noqa: BLE001
                return {"noted": True, "messageID": message_id, "publishError": str(e)}
        return {"noted": True, "messageID": message_id,
                "publishedToo": bool(already)}

    def backlink(self, ask, did):
        """A URL for the turn that produced a draft.

        **Publishing that turn is part of making the link**, not a side effect.
        A backlink to a withheld turn resolves to "reply not published" — a
        promise of context that delivers a placeholder, which is worse than no
        link. So the turn is published first, and if that fails there is no link
        to give.
        """
        session_id, message_id = ask.get("session"), ask.get("message")
        if not session_id or not message_id:
            raise actions.ActionError("backlink needs a session and a message")
        if not state.owns(session_id, did):
            raise actions.ActionError("no such session")

        raw = self.from_opencode(f"/session/{session_id}/message")
        turns = publish.turns_from(raw)
        if not any(t["id"] == message_id for t in turns):
            raise actions.ActionError("that turn is not in this conversation")

        already = set(publish.status(session_id, did)["published"])
        out = publish.reconcile(session_id, turns, already | {message_id}, did)
        if out["failed"]:
            raise actions.ActionError(
                "could not publish the turn to link back to: " + out["failed"][0]["error"])

        entry = ((publish._load().get(did) or {}).get(session_id)) or {}
        rkey = (entry.get("messages") or {}).get(message_id, {}).get("rkey")
        session_rkey = (entry.get("session") or "").rsplit("/", 1)[-1]
        if not rkey or not session_rkey:
            raise actions.ActionError("that turn has no record to link to")

        handle = self.handle_for(did)
        return {"uri": (f"{READER}/chat.html?handle={urllib.parse.quote(handle)}"
                        f"&session={session_rkey}#m-{rkey}")}

    def from_opencode(self, path):
        request = urllib.request.Request(f"{OPENCODE}{path}", headers=self.upstream_headers())
        with urllib.request.urlopen(request, timeout=60) as r:
            return json.loads(r.read())

    def whoami(self, did):
        """Who this browser is acting as.

        The handle comes from the network rather than from users.json, because a
        handle moves and a DID does not — the stored one is whatever it was when
        they were approved, which could be months of stale. Falls back to the
        stored value, then to the DID: a header that says who you are is worth
        more than one that says nothing while a lookup is slow.
        """
        handle = self.handle_for(did)
        if handle == did:
            handle = (state.users.get(did) or {}).get("handle") or did
        return self.reply(200, {"did": did, "handle": handle})

    # ---- writing to Bluesky ---------------------------------------------

    def perform_action(self, did):
        """Like, repost, reply, quote, post, undo — as the logged-in person.

        This is the one place anything in this project writes to Bluesky on a
        button press, and it is deliberately not reachable by the agent: there
        is no tool for it, only a route the browser calls when somebody clicks.
        The DID comes from the cookie, never from the body, so a request cannot
        ask to act as anyone else.
        """
        if self.command != "POST":
            return self.reply(405, {"error": "POST only"})
        try:
            payload = json.loads(self.body_bytes() or b"{}")
        except json.JSONDecodeError:
            return self.reply(400, {"error": "body is not JSON"})
        try:
            if payload.get("backlink"):
                payload["link"] = self.backlink(payload["backlink"], did)
            out = actions.perform(payload, did)
            # Give anything newly posted an index, so the page can tell the
            # agent about it in the same `[N]` language everything else uses and
            # the agent can call show-post on it without being handed a URI to
            # copy. The card it draws is the user's confirmation of what went
            # out, and — because a rendered card is what the publish path reads
            # refs from — it is also what makes the post visible on the reader.
            if out.get("uri") and payload.get("action") in ("post", "reply", "quote"):
                out["index"] = post_index.assign_indices([out["uri"]])[out["uri"]]
                out.update(self.record_action(payload, out, did))
            return self.reply(200, out)
        except actions.ActionError as e:
            # 400 with the reason: these are all things the person can act on —
            # too long, already deleted, not yours.
            return self.reply(400, {"error": str(e)})

    # ---- opencode -------------------------------------------------------

    # Exactly what the page needs upstream, and nothing else.
    #
    # Forwarding the whole `/session` tree was a mistake, and this is what it
    # cost: opencode also serves `POST /session/<id>/shell` ("Execute a shell
    # command within the session context") and `POST /session/<id>/command`,
    # and **both take an `agent`** — as does session creation, which takes a
    # `permission` block of its own on top. The model and agent checks ran on
    # `prompt_async` only, so any logged-in browser could have asked any of the
    # other three for the agent that has bash, and walked around the per-user
    # allowances entirely.
    #
    # An allowlist rather than three more checks, because the failure was not
    # that a check was missing — it was that the surface was whatever opencode
    # happened to serve. A new endpoint upstream must not become reachable here
    # by appearing.
    UPSTREAM = {
        ("POST", ("session",)),
        ("GET", ("session", "*")),
        ("GET", ("session", "*", "message")),
        ("POST", ("session", "*", "abort")),
        ("POST", ("session", "*", "prompt_async")),
    }

    def forwardable(self, method, parts):
        shape = tuple("*" if i == 1 else p for i, p in enumerate(parts))
        return (method, shape) in self.UPSTREAM

    def pass_to_opencode(self, method, url, did):
        parts = [p for p in url.path.split("/") if p]
        if not self.forwardable(method, parts):
            return self.reply(404, {"error": "not found"})
        # /session/<id>/... — anything naming a session must name one of yours.
        if len(parts) >= 2 and parts[0] == "session":
            if not state.owns(parts[1], did):
                return self.reply(404, {"error": "no such session"})

        body = self.body_bytes()
        if method == "POST":
            # Session creation carries `agent` and `model` too, and they outlive
            # the request that set them — so it is checked like a prompt. Its
            # tools are not imposed here (it takes no `tools` field); every
            # prompt into that session gets them.
            creating = parts == ["session"]
            body, refusal = self.with_checked_prompt(body, did, impose_tools=not creating)
            if refusal:
                return self.reply(400, {"error": refusal})
        request = urllib.request.Request(
            f"{OPENCODE}{url.path}" + (f"?{url.query}" if url.query else ""),
            data=body if method == "POST" else None,
            headers=self.upstream_headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as r:
                payload = r.read()
                status = r.status
                ctype = r.headers.get("content-type", "application/json")
        except urllib.error.HTTPError as e:
            payload, status, ctype = e.read(), e.code, "application/json"
        except OSError as e:
            return self.reply(502, {"error": f"opencode unreachable: {e}"})

        # A newly created session belongs to whoever asked for it. This is the
        # only place ownership is established, which is why it is established
        # from opencode's own answer rather than from anything the client said.
        if method == "POST" and url.path == "/session" and status < 300:
            try:
                state.own(json.loads(payload)["id"], did)
            except (json.JSONDecodeError, KeyError):
                pass
        return self.reply(status, payload, ctype)

    def stream_events(self, did):
        """opencode's SSE stream, with everything that is not yours removed."""
        try:
            upstream = urllib.request.urlopen(
                urllib.request.Request(f"{OPENCODE}/event", headers=self.upstream_headers()),
                timeout=None,
            )
        except OSError as e:
            return self.reply(502, {"error": f"opencode unreachable: {e}"})

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        block = []
        try:
            for raw in upstream:
                line = raw.decode("utf-8", "replace")
                if line.strip():
                    block.append(line)
                    continue
                if block and self.forward(block, did):
                    self.wfile.write(("".join(block) + "\n").encode())
                    self.wfile.flush()
                block = []
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser went away, which is the normal ending
        finally:
            upstream.close()

    def forward(self, block, did):
        """Whether one SSE event belongs to this user. Fail closed."""
        for line in block:
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                return False
            if event.get("type") in GLOBAL_EVENTS:
                return True
            props = event.get("properties") or {}
            info = props.get("info") if isinstance(props.get("info"), dict) else {}
            session_id = (props.get("sessionID") or info.get("sessionID")
                          or (info.get("id") if event.get("type", "").startswith("session.") else None))
            return bool(session_id) and state.owns(session_id, did)
        return False

    # ---- static ---------------------------------------------------------

    def serve_static(self, path):
        # `/shared/` is the components both halves of aligned.click use — the
        # vendored libraries, the colour tokens, the redaction bar. They live
        # inside `reader/` because that directory is what GitHub Pages uploads,
        # and the reader cannot reach outside it. Both sites ask for the same
        # `/shared/…` URL; only this line knows they come from different disks.
        if path.startswith("/shared/"):
            root, rel = SHARED, path[len("/shared/"):]
        else:
            root, rel = PUBLIC, path.lstrip("/") or "index.html"
        target = (root / rel).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            return self.reply(404, {"error": "not found"})
        if not target.is_file():
            return self.reply(404, {"error": "not found"})
        ctype = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        return self.reply(200, target.read_bytes(), ctype)


# Shared look: the reader's tokens, so every page of aligned.click is one thing.
STYLE = """<style>
 :root{color-scheme:light dark;--accent:#2f6f5e;--accent-fill:#2f6f5e;--bg:#fff;
       --fg:#1a1a1a;--muted:#6b7280;--border:#d1d5db;--panel:#f7f8f8}
 @media(prefers-color-scheme:dark){:root{--accent:#4e9d85;--accent-fill:#2a6353;
       --bg:#17181c;--fg:#e8e8e8;--muted:#9aa0a6;--border:#2c2d33;--panel:#1f2025}}
 *{box-sizing:border-box}
 body{font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
      display:flex;min-height:100dvh;margin:0;align-items:center;justify-content:center;
      padding:24px;background:var(--bg);color:var(--fg)}
 main{width:min(400px,100%)}
 h1{font-size:19px;margin:0 0 2px;letter-spacing:-0.01em}
 h1 .dot{color:var(--accent)}
 .step{font-size:12px;color:var(--muted);margin:0 0 18px;letter-spacing:.02em}
 h2{font-size:16px;margin:0 0 6px}
 p{color:var(--muted);font-size:14px;margin:0 0 16px}
 /* 16px, or Safari zooms the page when a field takes focus and never zooms back. */
 input,button,.btn{font:inherit;font-size:16px;width:100%;padding:12px;border-radius:8px;
      min-height:44px;display:block;text-align:center;text-decoration:none}
 input{border:1px solid var(--border);background:transparent;color:inherit;
      margin-bottom:10px;text-align:left}
 button,.btn.primary{border:0;background:var(--accent-fill);color:#fff;cursor:pointer}
 .btn.quiet{border:1px solid var(--border);background:var(--panel);color:var(--fg);
      margin-bottom:8px}
 .link{background:none;border:0;color:var(--accent);font-size:14px;cursor:pointer;
      padding:10px 0;min-height:0;width:auto;text-align:left}
 code{background:#8883;padding:2px 6px;border-radius:4px;font-size:13px;word-break:break-all}
 [hidden]{display:none}
</style>"""

# Three steps, and the third does two jobs. "Ask to join" and "sign in" are the
# same act: signing in proves you hold the handle, so a request recorded that
# way is a verified identity rather than a name somebody typed into a form. An
# unauthenticated request form would take anything, and the allowlist needs a
# DID, which only a login can supply.
LOGIN_PAGE = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name=theme-color content="#2f6f5e">
<title>aligned.click</title>
""" + STYLE + """
<main>
  <h1>aligned<span class=dot>.</span>click</h1>

  <section id=s1>
    <p class=step>Step 1 of 3 &middot; your identity</p>
    <h2>You sign in with an atproto account</h2>
    <p>Not an account here — one you own, on the network. Everything this makes
       is published to your repo under your name, and works the same if you
       stop using this site.</p>
    <button onclick="go(3)">I have one</button>
    <p style="margin:14px 0 6px">Otherwise, create one:</p>
    <a class="btn quiet" href="https://eurosky.tech/accounts" target=_blank rel=noopener>Eurosky &mdash; European hosting</a>
    <a class="btn quiet" href="https://bsky.app" target=_blank rel=noopener>Bluesky</a>
    <button class=link onclick="go(2)">What is this site? &rarr;</button>
  </section>

  <section id=s2 hidden>
    <p class=step>Step 2 of 3 &middot; access</p>
    <h2>It is invite-only for now</h2>
    <p>An agent that reads Bluesky with you and publishes what you decide to
       publish. Every turn costs energy on somebody's hardware, so it opens
       slowly.</p>
    <p>Signing in <em>is</em> the request &mdash; it proves the account is
       yours. Nothing is granted by asking, and nothing is posted without you
       pressing a button.</p>
    <button onclick="go(3)">Ask to join</button>
    <button class=link onclick="go(1)">&larr; Back</button>
  </section>

  <section id=s3 hidden>
    <p class=step>Step 3 of 3 &middot; sign in</p>
    <h2>Sign in</h2>
    <p>You are sent to your own server to do it. Nothing here ever sees your
       password.</p>
    <form action=/login>
      <input name=handle placeholder="you.bsky.social" autocapitalize=none
             autocorrect=off autocomplete=username spellcheck=false>
      <button>Continue</button>
    </form>
    <button class=link onclick="go(1)">&larr; Back</button>
  </section>
</main>
<script>
  function go(n) {
    for (const i of [1, 2, 3]) document.getElementById("s" + i).hidden = i !== n;
    location.hash = n > 1 ? "step" + n : "";
    const f = document.querySelector("#s3 input");
    if (n === 3) setTimeout(() => f.focus(), 0);
  }
  // A handle in the URL means somebody was sent straight here, so skip ahead.
  if (new URLSearchParams(location.search).get("handle") !== null) go(3);
  else if (location.hash === "#step3") go(3);
  else if (location.hash === "#step2") go(2);
</script>
"""

WAITING = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name=theme-color content="#2f6f5e">
<title>aligned.click</title>
""" + STYLE + """
<main>
  <h1>aligned<span class=dot>.</span>click</h1>
  <p class=step>Step 3 of 3 &middot; asked</p>
  <h2>You are on the list</h2>
  <p>Signed in as <strong>@{handle}</strong> &mdash; so the account is confirmed
     as yours. Access is granted by hand, and you will not hear from this page
     again; try signing in later.</p>
  <p>Recorded as:</p>
  <p><code>{did}</code></p>
</main>
"""

NOT_INVITED = WAITING


def notify_waitlist(did, handle):
    """Tell the operator somebody asked. Best effort, and never in the way of
    the answer: a webhook that is down must not turn a request into an error for
    the person who made it."""
    print(f"[waitlist] @{handle} ({did}) asked for access", file=sys.stderr)
    if not WAITLIST_WEBHOOK:
        return
    body = json.dumps({
        "title": "aligned.click",
        "message": f"@{handle} asked for access",
        "did": did,
        "handle": handle,
    }).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            WAITLIST_WEBHOOK, data=body,
            headers={"Content-Type": "application/json"}), timeout=10).read()
    except OSError as e:
        print(f"[waitlist] could not notify: {e}", file=sys.stderr)


def approve(did):
    """Move somebody from the waitlist to the allowlist.

    Writes users.json; the running proxy notices the file changed and picks it
    up on the next request. No restart, which matters most in the other
    direction — removing somebody has to take effect immediately, not whenever
    the service is next bounced.
    """
    entry = state.waiting.get(did)
    if not entry and did not in state.users:
        sys.exit(f"{did} is not on the waitlist. `--waitlist` lists who is.")
    state.users[did] = {"handle": (entry or {}).get("handle", ""),
                        "added": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    save(USERS_FILE, state.users)
    state.waiting.pop(did, None)
    save(WAITLIST_FILE, state.waiting)
    print(f"approved @{state.users[did]['handle'] or did} — live on their next request")


def main():
    if "--waitlist" in sys.argv:
        if not state.waiting:
            print("nobody waiting.")
            return
        for did, info in sorted(state.waiting.items(), key=lambda kv: kv[1].get("requested", "")):
            print(f"  {info.get('requested', '?')}  @{info.get('handle', '?'):<28} {did}")
        print(f"\napprove one with:  python3 server/proxy.py --approve <did>")
        return

    if "--approve" in sys.argv:
        i = sys.argv.index("--approve")
        if i + 1 >= len(sys.argv):
            sys.exit("--approve needs a DID")
        return approve(sys.argv[i + 1])

    if "--users" in sys.argv:
        if not state.users:
            print(f"No users. Create {USERS_FILE} — invite-only means a file "
                  f"somebody types into:\n")
            print('  {\n    "did:plc:…": { "handle": "you.example.com" }\n  }')
            return
        for did, info in state.users.items():
            print(f"  {did}  {info.get('handle', '')}")
        return

    if not state.users:
        print(f"warning: no users in {USERS_FILE} — nobody can log in.", file=sys.stderr)
        print("         run `python3 server/proxy.py --users` for the shape.", file=sys.stderr)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"auth proxy:      http://127.0.0.1:{PORT}   "
          f"({len(state.users)} user(s), {'https' if PUBLIC_URL else 'http, dev'})")
    server.serve_forever()


if __name__ == "__main__":
    main()
