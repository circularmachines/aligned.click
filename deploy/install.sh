#!/usr/bin/env bash
# Install the aligned.click stack as systemd services on this machine.
#
#     sudo deploy/install.sh
#
# Run it from the checkout, on the machine that will run the server. It is
# idempotent: run it again after pulling new code and it will reinstall the
# units and restart the services.
#
# What it does NOT do, deliberately:
#
# - **It does not bring your secrets.** `.env`, `~/.cloudflared/` and opencode's
#   provider key are not in the repo and are not invented here. The script tells
#   you which are missing and refuses to pretend the service is working without
#   them.
# - **It does not open a port.** Nothing here listens outside loopback except
#   through the Cloudflare tunnel, which is an outbound connection.
# - **It does not run the services as root.** They run as SERVICE_USER, and the
#   only reason this needs sudo at all is to write unit files into /etc.
set -euo pipefail

SERVICE_USER="${SERVICE_USER:-atproto-server}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITS=(aligned-oauth aligned-opencode aligned-proxy aligned-tunnel)

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { red "run this with sudo — it writes unit files to /etc/systemd/system"; exit 1; }
id "$SERVICE_USER" >/dev/null 2>&1 || {
  red "no user '$SERVICE_USER'. Create it, or set SERVICE_USER=… and re-run."; exit 1; }

USER_HOME="$(getent passwd "$SERVICE_USER" | cut -d: -f6)"
run_as() { sudo -u "$SERVICE_USER" -H bash -lc "$*"; }

# Where a runtime is, if it is anywhere. Asking `command -v` alone was wrong and
# quietly so: run_as is a login shell, and that shell's PATH is the system
# default — it carries neither ~/.local/bin nor ~/.opencode/bin, which is where
# this script installs all three of these. So nothing it installed was ever
# found again, and every run reinstalled everything. Node tolerated that (a
# directory swap and a symlink); cloudflared did not, and took the deploy with
# it. Look in the place we install to, after the PATH and before giving up.
runtime() {  # runtime <command> <path we would have installed it to>
  local found
  found="$(run_as "command -v $1" 2>/dev/null || true)"
  [ -n "$found" ] || { [ -x "$2" ] && found="$2"; } || true
  printf '%s' "$found"
}

# ---------------------------------------------------------------- runtimes
#
# Everything is installed into the service user's home rather than system-wide.
# Nothing else on this machine wants these versions, and an install that lives
# in one directory is an install you can delete.

step "runtimes"

PYTHON="$(command -v python3 || true)"
[ -n "$PYTHON" ] || { red "python3 is not installed"; exit 1; }
echo "  python3      $PYTHON"

NODE="$(runtime node "$USER_HOME/.local/bin/node")"
if [ -z "$NODE" ]; then
  echo "  node         installing to $USER_HOME/.local/lib/node"
  NODE_VER=v24.18.1
  run_as "
    set -e
    mkdir -p ~/.local/lib ~/.local/bin ~/.cache
    cd ~/.cache
    curl -sSLO https://nodejs.org/dist/$NODE_VER/node-$NODE_VER-linux-x64.tar.xz
    curl -sSL https://nodejs.org/dist/$NODE_VER/SHASUMS256.txt -o SHASUMS256.txt
    grep 'node-$NODE_VER-linux-x64.tar.xz' SHASUMS256.txt | sha256sum -c -
    tar -xJf node-$NODE_VER-linux-x64.tar.xz -C ~/.local/lib
    rm -rf ~/.local/lib/node && mv ~/.local/lib/node-$NODE_VER-linux-x64 ~/.local/lib/node
    ln -sf ~/.local/lib/node/bin/node ~/.local/bin/node
    ln -sf ~/.local/lib/node/bin/npm  ~/.local/bin/npm
    ln -sf ~/.local/lib/node/bin/npx  ~/.local/bin/npx"
  NODE="$USER_HOME/.local/bin/node"
fi
echo "  node         $NODE ($($NODE --version))"

CLOUDFLARED="$(runtime cloudflared "$USER_HOME/.local/bin/cloudflared")"
if [ -z "$CLOUDFLARED" ]; then
  echo "  cloudflared  installing to $USER_HOME/.local/bin"
  # Download beside it, then rename over it. Writing the file in place fails
  # with ETXTBSY — "Text file busy" — whenever the tunnel is up, because this is
  # the binary it is running, and curl reports that as the entirely opaque
  # "(23) Failure writing output to destination". A rename swaps the directory
  # entry instead, which the running process neither notices nor minds; it keeps
  # the old inode until it is restarted, which is what we want anyway.
  run_as "
    set -e
    mkdir -p ~/.local/bin
    curl -sSL -o ~/.local/bin/.cloudflared.new \
      https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    chmod 755 ~/.local/bin/.cloudflared.new
    mv -f ~/.local/bin/.cloudflared.new ~/.local/bin/cloudflared"
  CLOUDFLARED="$USER_HOME/.local/bin/cloudflared"
fi
echo "  cloudflared  $CLOUDFLARED"

OPENCODE="$(runtime opencode "$USER_HOME/.opencode/bin/opencode")"
if [ -z "$OPENCODE" ]; then
  echo "  opencode     installing"
  run_as "curl -fsSL https://opencode.ai/install | bash"
  OPENCODE="$USER_HOME/.opencode/bin/opencode"
fi
[ -x "$OPENCODE" ] || { red "opencode did not install to $OPENCODE"; exit 1; }
echo "  opencode     $OPENCODE"

# ---------------------------------------------------------------- the code

step "the code"

chown -R "$SERVICE_USER":"$SERVICE_USER" "$REPO"
echo "  owner        $SERVICE_USER"

run_as "cd '$REPO/oauth' && PATH=\"$USER_HOME/.local/bin:\$PATH\" npm install --omit=dev --silent"
echo "  oauth deps   installed"

# The agent's tool wrappers import @opencode-ai/plugin, so they need it here
# too. This used to work by accident: node_modules travelled with the rsync, 62
# megabytes of another machine's install. It does not travel any more, and
# without this the thirteen Bluesky tools are the whole agent and none of them
# would load.
run_as "cd '$REPO/agent/.opencode' && PATH=\"$USER_HOME/.local/bin:\$PATH\" npm install --omit=dev --silent"
echo "  agent deps   installed"

install -d -m 700 -o "$SERVICE_USER" -g "$SERVICE_USER" "$REPO/private"
chown -R "$SERVICE_USER:$SERVICE_USER" "$REPO/agent"
echo "  private/     0700"

# ---------------------------------------------------------------- config

step "config"

ENV_FILE="$REPO/.env"
[ -f "$ENV_FILE" ] || { install -m 600 -o "$SERVICE_USER" -g "$SERVICE_USER" /dev/null "$ENV_FILE"; }
chmod 600 "$ENV_FILE"; chown "$SERVICE_USER":"$SERVICE_USER" "$ENV_FILE"

# opencode refuses anonymous callers when this is set. Generated rather than
# prompted for: it is shared between two processes on one machine and never
# typed by a person.
if ! grep -q '^OPENCODE_SERVER_PASSWORD=' "$ENV_FILE"; then
  printf '\n# opencode server password, generated by deploy/install.sh %s\nOPENCODE_SERVER_PASSWORD=%s\n' \
    "$(date -I)" "$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32)" >> "$ENV_FILE"
  echo "  generated OPENCODE_SERVER_PASSWORD"
fi

missing=()
grep -q '^PUBLIC_URL=' "$ENV_FILE" || missing+=("PUBLIC_URL=https://aligned.click in .env")
[ -f "$USER_HOME/.cloudflared/cert.pem" ] || missing+=("$USER_HOME/.cloudflared/cert.pem  (copy from the machine that ran 'cloudflared tunnel login')")
ls "$USER_HOME"/.cloudflared/*.json >/dev/null 2>&1 || missing+=("$USER_HOME/.cloudflared/<tunnel-id>.json  (copy it too)")
# The provider block moved into agent/opencode.json, so a checkout knows its own
# models and there is nothing to set up in opencode's global config. What it
# needs is the key that block refers to, and that is in .env.
grep -q '^GREENPT_API_KEY=.\+' "$ENV_FILE" \
  || missing+=("GREENPT_API_KEY=… in .env  (the model provider's key — every user's turns bill to it)")
[ -s "$REPO/private/users.json" ] || missing+=("$REPO/private/users.json  (who may log in — invite-only means a file somebody types into)")

# Credentials that no longer have a job. Left in place rather than edited, but
# worth saying: they are full write access to a Bluesky account, sitting in a
# file that is now read by four services.
if grep -qE '^(BSKY|ADMIN)_APP_PASSWORD=' "$ENV_FILE"; then
  warn "  note: .env still has an app password. Nothing reads it any more — see RELEASE.md, B."
fi

# ---------------------------------------------------------------- services

step "services"

for unit in "${UNITS[@]}"; do
  sed -e "s|%REPO%|$REPO|g" \
      -e "s|%SERVICE_USER%|$SERVICE_USER|g" \
      -e "s|%PYTHON%|$PYTHON|g" \
      -e "s|%NODE%|$NODE|g" \
      -e "s|%OPENCODE%|$OPENCODE|g" \
      -e "s|%CLOUDFLARED%|$CLOUDFLARED|g" \
      "$REPO/deploy/systemd/$unit.service" > "/etc/systemd/system/$unit.service"
  echo "  /etc/systemd/system/$unit.service"
done

systemctl daemon-reload

if [ ${#missing[@]} -gt 0 ]; then
  # Enabled so they start at boot once the missing pieces arrive, but not
  # started now — a service that comes up and immediately fails teaches you
  # nothing except to distrust the status output.
  systemctl enable "${UNITS[@]}" >/dev/null 2>&1
  step "not started — these are missing:"
  for m in "${missing[@]}"; do red "  $m"; done
  echo
  echo "Add them, then:  sudo systemctl start ${UNITS[*]}"
  exit 1
fi

systemctl enable --now "${UNITS[@]}" >/dev/null 2>&1
sleep 4

step "status"
ok=0
for unit in "${UNITS[@]}"; do
  s="$(systemctl is-active "$unit" || true)"
  if [ "$s" = active ]; then green "  $s   $unit"; else red "  $s   $unit"; ok=1; fi
done

echo
if [ "$ok" = 0 ]; then
  green "all four running, and they start at boot."
  echo "  logs:  journalctl -u aligned-proxy -f"
  echo "  check: $REPO/server/check-dns.sh"
else
  red "something did not start."
  echo "  journalctl -u <unit> -n 40 --no-pager"
  exit 1
fi
