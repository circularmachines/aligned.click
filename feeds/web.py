#!/usr/bin/env python3
"""A small local web front door for the feed builder.

Serves feeds/index.html plus a small API:

    GET  /api/feeds                          the feeds, with their progress
    POST /api/add {"text": "…"}              create a feed and assemble it
    POST /api/remove {"id": "…"}             delete a feed

Creating a feed immediately enqueues it for assembly: the background worker
runs crawl.assemble until the feed has FEEDS_GOAL posts (status: ready) or
gives up (status: stalled). The page polls /api/feeds to watch the progress
x/goal, with the keywords' own chips underneath.

Posts are not served here. The page shows each confirmed post as an
<atproto-post> element, which draws the post live from whichever PDS hosts its
author — the same split the reader uses, for the same reason.

`/shared/…` is served from reader/shared/, so the page and the two halves of
aligned.click use the one copy of atproto-wc plus the colour tokens.

    python3 feeds/web.py            # http://127.0.0.1:8782

Crawl needs the same .env as the CLI: INDEX_BLUESKY_HANDLE /
INDEX_BLUESKY_APP_PASSWORD to search, and GREENPT_API_KEY to judge.
"""
import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
# This module's own directory must win: feeds/ and index/ both ship a crawl.py,
# and a wrong pick here silently runs the index's crawler (whose main() takes
# no argv) behind the "Crawl one" button. Each insert(0) pushes earlier entries
# down, so the feeds dir goes in last to end up on top.
sys.path.insert(0, str(ROOT.parent / "cause"))
sys.path.insert(0, str(ROOT.parent / "index"))
sys.path.insert(0, str(ROOT.parent / "tools"))
sys.path.insert(0, str(ROOT))

# Import the feed crawler FIRST. feeds/ and index/ both ship a crawl.py, and
# web.py's own path (above) has index/ in it — so a bare `import crawl` after
# this block could silently bind the index's crawler, whose main() takes no
# argv, and the "Crawl one" button would die in a thread. Binding it here,
# while feeds/ is still the top of the path, is what picks ours.
import crawl  # noqa: E402
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

# One assembly worker at a time, so state writes are serialized. Pressing
# Create enqueues the new feed; the worker runs crawl.assemble(feed_id) until
# the feed is ready or stalled, then takes the next in line.
_work_lock = threading.Lock()
_worker = None
_queue: list[str] = []
_crawling = False
_last_crawl_error = None


def _set_crawling(value: bool) -> None:
    global _crawling
    _crawling = value


def _enqueue(feed_id: str) -> None:
    """Put a feed on the assembly queue and make sure a worker is running."""
    global _worker
    with _work_lock:
        _queue.append(feed_id)
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, daemon=True)
            _worker.start()


def _worker_loop() -> None:
    global _last_crawl_error
    while True:
        with _work_lock:
            if not _queue:
                _set_crawling(False)
                return
            feed_id = _queue.pop(0)
        _set_crawling(True)
        _last_crawl_error = None
        try:
            crawl.assemble(feed_id)
        except SystemExit:
            pass
        except Exception as e:  # noqa: BLE001 — keep the server alive, tell the page
            _last_crawl_error = f"assembly failed: {e}"
            print(_last_crawl_error, file=sys.stderr)


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

    def log_message(self, *a):  # keep the interactive console quiet
        pass

    # ---- routing ---------------------------------------------------------

    def do_GET(self):
        if self.path == "/":
            return self.reply(200, FEEDS_HTML.read_text(), "text/html; charset=utf-8")
        if self.path.startswith("/shared/"):
            return self.serve_static(self.path[len("/shared/"):])
        if self.path == "/api/feeds":
            feeds = state.load_feeds()
            return self.reply(200, {"feeds": feeds, "crawling": _crawling,
                                    "last_error": _last_crawl_error})
        return self.reply(404, {"error": "not found"})

    def do_POST(self):
        body = self.body()
        if self.path == "/api/add":
            return self.add(body)
        if self.path == "/api/remove":
            return self.remove(body)
        return self.reply(404, {"error": "not found"})

    # ---- API -------------------------------------------------------------

    def add(self, body):
        text = str(body.get("text") or "").strip()
        if not text:
            return self.reply(400, {"error": "the request is empty — say what "
                                    "kind of posts you want to see more of."})
        try:
            result = request.add(text)
        except Exception as e:  # noqa: BLE001 — a verdict/reason, not a traceback
            return self.reply(400, {"error": str(e)})
        feed_id = result["feed"]["id"]
        _enqueue(feed_id)
        return self.reply(200, {"id": feed_id, "seeds": result["seeds"],
                                "started": True})

    def remove(self, body):
        feed_id = body.get("id") or ""
        feeds = state.load_feeds()
        if feed_id not in feeds:
            return self.reply(404, {"error": f"no feed with id {feed_id}."})
        request.remove(feed_id)
        return self.reply(200, {"removed": True})

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