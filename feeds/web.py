#!/usr/bin/env python3
"""A small local web front door for the one-shot feed round.

Serves feeds/index.html plus one action:

    GET  /api/feeds        the feeds and their last suggestion batch
    POST /api/add {"text"} create a feed, then run the pipeline: seed the
                          per-post judge by criteria similarity from the
                          embedded post store and keep the fittings
                          (pipeline.py). Synchronous — the page shows the
                          result of the single call.

Posts are not served here. The page draws each pick as an <atproto-post>
element, which renders the post live from whichever PDS hosts its author —
the same split the reader uses, for the same reason.

`/shared/…` is served from reader/shared/, one copy of atproto-wc plus the
colour tokens.

    python3 feeds/web.py            # http://127.0.0.1:8782

Search needs the same .env as the CLI: INDEX_BLUESKY_HANDLE /
INDEX_BLUESKY_APP_PASSWORD to search, and GREENPT_API_KEY to select.
"""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT.parent / "index"))
sys.path.insert(0, str(ROOT))

import state  # noqa: E402
import request  # noqa: E402

PORT = int(__import__("os").environ.get("FEEDS_WEB_PORT", "8782"))
FEEDS_HTML = ROOT / "index.html"
SHARED = ROOT.parent / "reader" / "shared"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}

CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
       "connect-src 'self' https:; font-src 'self'; base-uri 'none'; "
       "frame-ancestors 'none'")


def log(*parts):
    print(f"[{time.strftime('%H:%M:%S')}] " + " ".join(str(p) for p in parts),
          file=sys.stderr, flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "aligned-feeds"

    # ---- plumbing -------------------------------------------------------

    def reply(self, status, body=b"", content_type="application/json; charset=utf-8"):
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
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}

    def send_error(self, code, message=None, explain=None):  # noqa: A003 — stdlib shape
        self.reply(code, {"error": message or "error"})

    def log_message(self, format, *args):  # the interactive console stays quiet;
        pass                              # log() handles the request lines

    def log_request(self, status):
        try:
            line = f"{self.command} {self.path} -> {status}"
        except Exception:  # noqa: BLE001
            line = f"{self.command} {self.path}"
        log(line)

    # ---- routing ---------------------------------------------------------

    def do_GET(self):
        if self.path == "/":
            return self.reply(200, FEEDS_HTML.read_text(), "text/html; charset=utf-8")
        if self.path.startswith("/shared/"):
            return self.serve_static(self.path[len("/shared/"):])
        if self.path == "/api/feeds":
            feeds = state.load_feeds()
            return self.reply(200, {"feeds": feeds})
        return self.reply(404, {"error": "not found"})

    def do_POST(self):
        body = self.body()
        if self.path == "/api/add":
            return self.add(body)
        return self.reply(404, {"error": "not found"})

    # ---- API -------------------------------------------------------------

    def add(self, body):
        text = str(body.get("text") or "").strip()
        if not text:
            return self.reply(400, {"error": "the request is empty — say what "
                                    "kind of posts you want to see more of."})
        try:
            result = request.add(text)
            feed = result["feed"]
            feeds = state.load_feeds()
        except Exception as e:  # noqa: BLE001 — a verdict/reason, not a traceback
            return self.reply(400, {"error": str(e)})
        return self.reply(200, {
            "id": feed["id"],
            "text": feed["text"],
            "criteria": feed.get("criteria"),
            "keywords": feed.get("keywords") or [],
            "suggested": feed["suggested"],
            "posts": feed.get("posts") or {},
            "round": feed.get("rounds", 0),
            "note": feed.get("note"),
        })

    # ---- static -----------------------------------------------------------

    def serve_static(self, rel):
        target = (SHARED / rel).resolve()
        try:
            target.relative_to(SHARED.resolve())
        except ValueError:
            return self.reply(404, {"error": "not found"})
        if not target.is_file():
            return self.reply(404, {"error": "not found"})
        ctype = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        return self.reply(200, target.read_bytes(), ctype)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=PORT,
                        help="port to serve on (default %(default)s)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"feeds at http://127.0.0.1:{args.port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()