#!/usr/bin/env bash
# Starts the OAuth sidecar, the opencode server and the static UI together.
# Ctrl-C stops all three.
set -euo pipefail

OPENCODE_PORT="${OPENCODE_PORT:-4096}"
PROXY_PORT="${PROXY_PORT:-8778}"
OAUTH_PORT="${OAUTH_PORT:-4098}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$DIR/agent"

cleanup() {
  kill "${OAUTH_PID:-}" "${OPENCODE_PID:-}" "${PROXY_PID:-}" "${TUNNEL_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Kill whatever is already bound to a port we need, so a stale server from a
# previous run doesn't block this one (or leave two fighting over the port).
free_port() {
  local port="$1" pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "$port/tcp" 2>/dev/null | tr -s ' ' || true)"
  fi
  if [ -n "$pids" ]; then
    echo "freeing port $port (killing PIDs: $pids)"
    kill $pids 2>/dev/null || true
    sleep 1
    kill -9 $pids 2>/dev/null || true  # force-kill any survivors
  fi
}

free_port "$OAUTH_PORT"
free_port "$OPENCODE_PORT"
free_port "$PROXY_PORT"

# Node and cloudflared live in ~/.local rather than on the system.
export PATH="$HOME/.local/bin:$PATH"

# Public hostname, if this machine is meant to be reachable. Its presence flips
# two things at once: the OAuth client becomes confidential (private_key_jwt,
# which is what makes a refresh token outlive a few days) and the session cookie
# becomes Secure. Absent, everything runs on loopback for development.
if [ -z "${PUBLIC_URL:-}" ] && [ -f "$DIR/.env" ]; then
  PUBLIC_URL="$(grep -m1 '^PUBLIC_URL=' "$DIR/.env" | cut -d= -f2- | tr -d '[:space:]' || true)"
fi
export PUBLIC_URL="${PUBLIC_URL:-}"

# opencode refuses anonymous callers when this is set, which is a second lock
# behind the proxy rather than a replacement for it. Generated on first run if
# absent — an unset password is the one case where opencode says out loud that
# it is unsecured, and it is right to.
if [ -z "${OPENCODE_SERVER_PASSWORD:-}" ] && [ -f "$DIR/.env" ]; then
  OPENCODE_SERVER_PASSWORD="$(grep -m1 '^OPENCODE_SERVER_PASSWORD=' "$DIR/.env" | cut -d= -f2- | tr -d '[:space:]' || true)"
fi
if [ -z "${OPENCODE_SERVER_PASSWORD:-}" ]; then
  OPENCODE_SERVER_PASSWORD="$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32)"
  printf '\n# opencode server password, generated %s\nOPENCODE_SERVER_PASSWORD=%s\n' \
    "$(date -I)" "$OPENCODE_SERVER_PASSWORD" >> "$DIR/.env"
  echo "generated an opencode server password and saved it to .env"
fi
export OPENCODE_SERVER_PASSWORD

# Deliberately no ACTING_DID here. A tool learns whose call it is from the
# session that caused it — opencode hands its wrapper a sessionID, the wrapper
# passes it down, and the proxy has already recorded who owns that session.
#
# Exporting one identity for the whole server would override that with whoever
# started it. Invisible with one user; with two, it answers one person's
# question using another person's view of the network, blocks and mutes
# included, and attributes anything published to the wrong repo.

# The sidecar holds the OAuth sessions and signs every request. Not optional
# infrastructure: no Python here can read Bluesky without it, by design — the
# DPoP key never leaves that process.
node "$DIR/oauth/server.mjs" &
OAUTH_PID=$!

# Wait for it rather than racing the first tool call against startup.
for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:$OAUTH_PORT/health" >/dev/null 2>&1 && break
  sleep 0.25
done
if ! curl -sf "http://127.0.0.1:$OAUTH_PORT/health" >/dev/null 2>&1; then
  echo "oauth sidecar did not start on port $OAUTH_PORT — installed? (cd oauth && npm install)" >&2
  exit 1
fi

# opencode's project directory defaults to its cwd, and everything it is
# configured by now lives in agent/ — opencode.json, the instructions it loads,
# the models it may run and the .opencode/tools/ wrappers. Started from there,
# it reads its own configuration directly instead of finding it by walking up
# out of an empty directory, and private/ is outside the tree it considers its
# project rather than sitting in the middle of it.
# No --cors: the page and the API are the same origin now, because the proxy
# serves both. There is no cross-origin request left to allow.
(cd "$AGENT_DIR" && opencode serve --port "$OPENCODE_PORT" --hostname 127.0.0.1) &
OPENCODE_PID=$!

# The auth proxy serves the UI and everything else. It is the only process here
# that knows who anybody is, and the only one that would ever be exposed.
python3 "$DIR/server/proxy.py" &
PROXY_PID=$!

# The tunnel, last: it is what makes any of this reachable, and by now the proxy
# in front of it is already refusing anonymous requests. Opening it earlier
# would mean a window with opencode exposed and nothing checking who is asking.
if [ -n "$PUBLIC_URL" ] && command -v cloudflared >/dev/null 2>&1; then
  cloudflared tunnel --config "$DIR/server/tunnel.yml" run &
  TUNNEL_PID=$!
  echo "public:          $PUBLIC_URL"
fi

echo "opencode server: http://127.0.0.1:$OPENCODE_PORT  (behind the proxy)"

wait
