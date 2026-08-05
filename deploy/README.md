# Deploying to the mini-PC

`atproto-server@192.168.86.250`, SSH on the default port. Ubuntu 24.04, x86_64,
sudo prompts for a password. The `250` is the last octet of the address — this
document used to say `ssh -p 250`, which was never a port anything listened on.

Four services, started by systemd at boot, none of them listening on a port
anybody outside can reach. The only way in is the Cloudflare tunnel, which is
an outbound connection, and it terminates at the auth proxy.

    aligned-oauth      the OAuth sidecar  — holds every session, signs every request
    aligned-opencode   the agent          — loopback only, password-locked
    aligned-proxy      the auth proxy     — the only thing that knows who anyone is
    aligned-tunnel     cloudflared        — aligned.click

The ordering between them is a safety property rather than a preference. The
tunnel `BindsTo` the proxy, so it cannot be what is running if the proxy is
not — otherwise a crashed proxy would leave a public door with nothing behind
it checking who is asking.

## Getting the code there

    rsync -av --delete --filter=':- .gitignore' --exclude .git \
      ./ atproto-server@192.168.86.250:~/aligned.click/

Or clone it. Either way **nothing untracked may travel**, which is why the
excludes are read from `.gitignore` rather than listed here. A hand-written list
is a list somebody has to remember to update, and the one this replaced had
already fallen behind twice:

- `tools/.session*.json` — cached Bluesky session tokens, `accessJwt` and
  `refreshJwt` for the admin account. Gitignored for exactly that reason, and
  copied to the server by the old command.
- `agent/.opencode/node_modules` — 62MB of installed dependencies, which is
  also 62MB of build output from a different machine. The rule now sends 1.1MB.

`.env` and `private/` were already excluded and still are: one holds secrets,
the other every logged-in person's refresh tokens. The difference is that they
are excluded *because git ignores them*, so the next thing that must not travel
is covered by having been gitignored, without anyone editing this command.

## Installing

    ssh atproto-server@192.168.86.250
    cd ~/aligned.click
    sudo deploy/install.sh

It installs node, cloudflared and opencode into the service user's home if they
are absent, installs the units, and starts everything. Run it again after
pulling new code — it is idempotent, and reinstalling the units is how you pick
up a change to them.

**sudo is only for writing into `/etc/systemd/system`.** The services themselves
run as `atproto-server`.

## The four things it will not do for you

The installer refuses to start anything until these exist, and names the ones
that are missing. All four are credentials, which is exactly why they are not in
the repo:

1. **`.env`** — needs `PUBLIC_URL=https://aligned.click` and
   `GREENPT_API_KEY`. The opencode server password is generated for you. See
   `.env.example`, which lists every variable anything here actually reads.

   **Copying `.env` from the laptop is not enough.** On that machine
   `GREENPT_API_KEY` is exported from `~/.bashrc`, so it is not in the file —
   which is why everything works there and why `.env` looks complete when it is
   not. systemd never sources a shell profile: the units load `.env` and
   nothing else, so the key has to be *in* it here. Without it the services all
   start cleanly and every turn fails at the provider.
2. **`~/.cloudflared/cert.pem` and `~/.cloudflared/<tunnel-id>.json`** — copy
   both from the machine that ran `cloudflared tunnel login`. The tunnel is
   already created; a second `login` on this machine is not needed and would
   only add another certificate.
3. ~~`~/.config/opencode/opencode.jsonc`~~ — **no longer needed.** The provider
   block lives in `agent/opencode.json` now, so a checkout knows its own models,
   and it reads the key from `GREENPT_API_KEY` in `.env` (item 1). Every user's
   turns bill to that one key, which is why the proxy rate-limits per DID.
4. **`private/users.json`** — who may log in:

       { "did:plc:…": { "handle": "you.example.com" } }

   Optionally `models`, `tools` and `agents` per person — absent means
   everything this server offers. `agents` is what gates `builder`, the one
   that can run commands, so leave it off for everybody but yourself.

   Invite-only means a file somebody types into. A successful login by a DID
   that is not in it is a polite refusal, not an account.

## Afterwards

    systemctl status aligned-proxy
    journalctl -u aligned-proxy -f
    ./server/check-dns.sh

Then open https://aligned.click and log in. The first login from this
machine is also the first exercise of confidential-client OAuth from here, so
if something is going to be wrong it will be that.

## Updating

    git pull && sudo deploy/install.sh

## Removing it

    sudo systemctl disable --now aligned-tunnel aligned-proxy aligned-opencode aligned-oauth
    sudo rm /etc/systemd/system/aligned-*.service
    sudo systemctl daemon-reload

That leaves the checkout, `~/.local` and the credentials. Deleting
`private/oauth/sessions.json` is what actually logs everybody out.
