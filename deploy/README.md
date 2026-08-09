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

Clone it. The repo is public, so this needs no key on the server:

    git clone https://tangled.org/aligned.click/agent ~/aligned.click

Updating later is `git pull && sudo deploy/install.sh`. This is how it was
first installed, deliberately: doing it from a clone rather than by copying a
working directory is also the test of whether anyone else could stand it up.

If you must push a working copy instead — an unpushed fix, a bisect —

    rsync -av --delete --filter=':- .gitignore' --exclude .git \
      ./ atproto-server@192.168.86.250:~/aligned.click/

**Nothing untracked may travel**, which is why the
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
4. **`private/` — the parts the services read, copied file by file.** Not the
   directory. On the laptop it also holds the strategizer's material —
   `strategist/`, `fetches/` with scraped LinkedIn and Instagram data,
   `creators.json`, `analysis.db`, `external.db` — and none of that belongs on
   a server that is on the internet. `rsync private/` is one word shorter and
   sends all of it.

   What the services actually read:

       users.json  waitlist.json  published.json  proxy-sessions.json
       oauth/client-key.json  oauth/sessions.json  oauth/state.json

   `oauth/client-key.json` is the confidential client's key and logins break
   without it. Bringing `oauth/sessions.json` and `proxy-sessions.json` is what
   makes existing logins survive the move; leave them behind and everyone signs
   in again, which is also a fine choice.

   `users.json` is who may log in:

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

Then open https://aligned.click and log in. If you brought `oauth/` across you
are already logged in; otherwise this is the first exercise of
confidential-client OAuth from this machine, so if something is going to be
wrong it will be that.

**Two checks worth making that a green `systemctl status` will not make for
you**, because both fail with all four services reporting active:

    # the provider key actually resolved, rather than staying a placeholder
    grep -c '^GREENPT_API_KEY=.\+' .env

    # the thirteen tools registered — ask opencode, do not read the config
    # that was supposed to produce them
    curl -su "opencode:$(grep '^OPENCODE_SERVER_PASSWORD=' .env | cut -d= -f2) " \
      http://127.0.0.1:4096/experimental/tool/ids | tr ',' '\n' | grep -c '"'

The second one matters because the installer fetches whatever opencode is
current — 1.18.13 at the time of writing — while the wrappers pin
`@opencode-ai/plugin` to 1.16.2. A version gap there produces an agent with no
tools and no error message.

## The first login, on a machine with no users

Fresh, `private/users.json` is empty and nobody can log in — which is what
invite-only means, and it is also a chicken-and-egg to walk through once.

**A person becomes the first member by being turned down.** Open the site and
sign in. Signing in *is* the request, so it puts you on the waitlist and grants
nothing. Then, on the server:

    python3 server/proxy.py --waitlist          # shows the DID that just asked
    python3 server/proxy.py --approve <did>     # live on their next request

**The admin account is a separate thing, and it is not a member.** `ADMIN_DID`
is the account owning the authorising domain — `aligned.click` itself. It never
chats. It exists to write two kinds of record under the domain's own name: the
lexicon schemas (`publish/lexicons.py --publish`) and the member list
(`publish/members.py`). What it needs is a session in the sidecar, and nothing
else.

It gets one the same way anybody does — open the site, sign in as that account.
**It will land on the waitlist page, and that is correct.** The sidecar stores
the session at the OAuth callback, before the proxy checks the allowlist at all,
so the session is kept even though the login was refused. Do *not* approve it:
approving would make the project account a chat user, which it has no reason to
be. Take it off the waitlist if the entry bothers you.

Then name it, so the writers stop guessing:

    echo 'ADMIN_DID=did:plc:…' >> .env      # the DID of aligned.click itself

There is no app password for this and there should not be. A stored OAuth
session is scoped and can be revoked from the account; an app password is a
permanent credential to the whole account, and this project removed the last one
on purpose (`RELEASE.md` §B).

**Ordering does not matter.** `--approve` writes the member record if it can and
says what to run by hand if it cannot — a missing `ADMIN_DID` prints a line, it
does not undo the approval. So approving people before the admin account exists
is fine; catch the list up afterwards with:

    python3 publish/members.py --import       # from users.json
    python3 publish/members.py                # read back what is published

If the session ever lapses — it is used rarely, which is exactly when a session
lapses — the symptom is `--approve` printing that it could not list somebody.
The fix is to sign in as that account again.

## Updating

For a change that is only code — the proxy, the page, the tools — pull it and
restart the service that runs it. This is the common case:

    git pull && sudo systemctl restart aligned-proxy

`install.sh` is for when the *installation* changes: a new or edited unit file,
a runtime that has to be fetched, a new service user. It reinstalls the units
and restarts all four, so reaching for it to pick up an edited Python file is a
much bigger hammer than the job needs — and it restarts the tunnel, which a code
change has no reason to disturb.

Either way, the proxy is worth a look afterwards rather than a `systemctl
is-active`, which reports a wedged process as running:

    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8778/healthz

## Moving it from another machine

`install.sh` runs `systemctl enable --now` on all four units, so the tunnel
starts as part of installing. **Stop the old connector first.** A named
Cloudflare tunnel accepts several connectors and load-balances between them, so
two running at once means requests land on whichever host answers — including
one you have not verified yet.

    # on the machine that was serving
    pkill -x cloudflared

Then install, then verify, and the rollback while you do is to start the old
connector again.

## Removing it

    sudo systemctl disable --now aligned-tunnel aligned-proxy aligned-opencode aligned-oauth
    sudo rm /etc/systemd/system/aligned-*.service
    sudo systemctl daemon-reload

That leaves the checkout, `~/.local` and the credentials. Deleting
`private/oauth/sessions.json` is what actually logs everybody out.
