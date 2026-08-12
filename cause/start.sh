#!/usr/bin/env bash
# The CAUSE prototype, self-contained: its own dev-mode OAuth sidecar plus the
# web app.
#
# The sidecar that normally runs on 4098 is in production mode and routes login
# callbacks through the public tunnel. A prototype should not depend on that,
# so this starts a second sidecar in loopback mode whose redirect lands on the
# prototype itself — logins work with the tunnel down and nothing else running.
#
#     ./cause/start.sh                 # http://127.0.0.1:8780
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$DIR")"
CAUSE_PORT="${CAUSE_PORT:-8780}"
OAUTH_PORT="${OAUTH_PORT:-4099}"
SIDECAR="http://127.0.0.1:${OAUTH_PORT}"

cleanup() { [ -n "${OAUTH_PID:-}" ] && kill "$OAUTH_PID" 2>/dev/null || true; }
trap cleanup EXIT

free_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:$port" 2>/dev/null | xargs -r kill 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k "$port/tcp" >/dev/null 2>&1 || true
  fi
}
free_port "$CAUSE_PORT"
free_port "$OAUTH_PORT"

echo "starting dev OAuth sidecar on :$OAUTH_PORT (loopback mode)"
(
  cd "$REPO/oauth"
  PUBLIC_URL= PROXY_URL="http://127.0.0.1:${CAUSE_PORT}" OAUTH_PORT="$OAUTH_PORT" node server.mjs
) &
OAUTH_PID=$!

for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${OAUTH_PORT}/health" >/dev/null 2>&1 && break
  sleep 0.25
done
curl -sf "http://127.0.0.1:${OAUTH_PORT}/health" >/dev/null || { echo "oauth sidecar did not start" >&2; exit 1; }

echo "starting CAUSE prototype on http://127.0.0.1:${CAUSE_PORT}"
OAUTH_SIDECAR="$SIDECAR" python3 "$DIR/app.py"