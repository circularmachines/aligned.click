# RELEASE — v1

**Target: a few days from 2026-08-03.** This is the checklist, not a plan. Every
box is either done, or it is work someone has to do before the thing is on the
internet with another person's account behind it.

## What v1 is

An agent that reads Bluesky and publishes conversations to atproto, running on
Johan's home PC, reachable from anywhere, usable by a small number of invited
people who each publish as themselves.

Three things make that sentence different from what runs today, and they are
the whole release:

1. **Other people, logging in as themselves.** Today there is one identity in
   one `.env`, held as an app password. v1 has atproto OAuth and no app
   passwords at all — `johan.aligned.click` included.
2. **Off localhost.** Today everything binds `127.0.0.1` and trusts whatever
   reaches it.
3. **On a phone.** Today both frontends are desktop-only in a way that is not a
   matter of taste — see §F.

## What runs where

```
  phone / laptop
        │  https
        ▼
  aligned.click ──────► auth proxy ──┬─► opencode server (one, shared)
  (Cloudflare Tunnel,    OAuth login  │      │    users' agent cannot write
   no open ports)        session→user │      │       password-locked too
                         session→DID  │      │       rate limit per user
                                      │      └─► greenpt proxy ─► GreenPT
                                      │           (tees `impact`)   ▲ one key,
                                      │                             │ yours
                                      └─► the chat UI (served by the proxy)
                                            + publish endpoint, as the session's DID

  read.aligned.click ──► GitHub Pages ──► reads atproto directly, no backend
                                          never calls aligned.click
```

Two properties hold this together and both are checked below: **the agent users
get cannot write anything**, which is what makes one shared workspace safe, and
**the proxy is the only thing that knows who anyone is**, which is what makes a
publish land in the right repo.

"the agent users get" is doing real work in that sentence as of 2026-08-05.
There is one that can write — `builder`, bash and edit, for Johan alone — and
it is reachable only by naming it in the prompt *and* being listed for it in
`users.json`. It is not sandboxed. See §B, "One shared workspace".

The reader is already live and has no backend, so it is not in the risk surface
of this release. Everything below concerns the other half.

---

## A. Split the repo — decide what ships publicly

The code goes public on tangled.org at release. The strategizer, the scraping
machinery and the creator data are not part of the thing being released, and
some of it must not be in a public repo at all.

### History is dropped — decided

**Re-init for the first release.** The public repo starts at commit one with the
cleaned tree; this repository stays private on GitHub as the reference copy of
how it got here.

That is the right call and it is not paranoia. Measured here, 2026-08-03:

    STRATEGIST.md              13 commits, real creator name in 5 of them
    public/products/strategist  4 commits
    sync/                       6 commits
    47 commits total.  private/ has never been tracked — that part is clean.

Deleting a file, gitignoring it, or moving it to a branch does nothing to any of
that; only new history does.

**Decided: this repo becomes read-only reference.** Development moves to the new
one at `git init`; nothing is cherry-picked back. That removes the divergence
question rather than answering it, which is the only reliable way to handle two
trees.

- [x] **Done 2026-08-05.** The 117 commits of history were pushed to
      `at_opencode` *first* and verified matching on both ends, then the tree
      was re-initialised in place — one commit, 85 files, on `main`. In place
      rather than in a new directory, because `/home/johan/code/aligned.click`
      is written into `.env`, `private/` and the systemd units.

      Published to both forges from one remote with two push URLs: fetch from
      `tangled.org` (canonical), push to tangled and to
      `github.com/circularmachines/aligned.click` (the mirror, which exists so
      GitHub Actions can deploy the reader to Pages). Note that this
      arrangement lives in `.git/config` — it is a property of that working
      copy and does not travel to a clone.

      The tangled remote is a **repo DID**, not `handle/repo`:
      `git@tangled.org:did:plc:4ubwcjik6lc44ef5hiqknm7r`. The DID resolves to
      no handle at all, which is why guessing the path was never going to work.
      Pushing needs an ssh key published to the atproto account that owns the
      repo — the knot identifies pushes by key, not by password.
- [x] **The name audit was re-run on the seed tree**, as this section said to.
      2,242 candidate names harvested from `private/` — every creator, contact
      and company in the parked material — checked against the tracked tree with
      `git grep`. Two hits, both Johan's own name in the reader's copyright
      header. A first attempt reported ~200 hits and was wrong: the regex
      matched across line breaks and harvested "The", "What", "Login" as names.
- [ ] **Say so in the old repo** — a line at the top of `at_opencode`'s README
      naming this one and the date it stopped. It is *that* repo that needs the
      notice, not this one, and it needs doing there. A reference repo nobody
      can tell is a reference repo gets edited.
- [ ] **Confirm `at_opencode` is private**, and stays that way. Nothing about
      the re-init makes the old history safe to publish later — it holds the
      creator's name in five commits.

### Clean the tree — done 2026-08-03

Five commits on `main` here, `2ea0bfa..902a49a`. The seed tree is what gets
committed at `git init`, so this had to be right first.

- [x] **`STRATEGIST.md`, `public/products/strategist/` and the `strategist`
      agent block** — parked in `private/strategist/`, paths mirrored, with a
      README saying what left and why.
- [x] **The product mechanism kept, generic now.** It inferred the product from
      `?creator=`, which made it single-tenant by construction; `?product=`
      names it directly and every other query parameter substitutes into the
      template as `{name}`. No product means an empty chat, which is v1.
- [x] **`sync/` does not ship** — the acquisition half, parked whole.
- [x] **The creator tools do not ship** — `connections`, `creator-items`, and
      then `creator_index`, `analysis_index` and `vision`, which had no callers
      left once the tools below went.
- [x] **The worker workflow dropped entirely** — `delegate`, `append-note`,
      `search-notes`, `WORKER.md`, the agent block, the `OPENCODE_ATTACH_URL`
      export, and the AGENTS.md section. Nothing writes to the shared workspace
      now, which is what makes §B's shared workspace safe.
- [x] **`show-draft` and `analyze-image` deleted.** Both required `--creator`
      and opened the creator store before doing anything, so both had become
      dead in v1 — they printed "nothing has been synced" and drew nothing.
      `analyze-image` has never seen an atproto image: it reads `--ref ig#3`
      and image paths on this disk. Neither was fixable by moving.
- [x] **`create-draft` added in show-draft's place** — the same card without
      the creator store. Text in, text on screen, editable, counted against the
      300-grapheme limit. Named `create-draft`, not `create-post`, because a
      tool called create-post invites a model to report that it posted
      something. Text only until there is a blob to attach.
- [x] **`/media/` gone from `serve.py`**, which was the §B item and is now the
      only reason that file still exists. Nothing under `private/` is served.
- [x] **`creators.example.json` gone** — config for the parked importers.
- [x] **Name audit clean.** No occurrence of the creator's name anywhere in the
      51 tracked files. Re-run it on the seed tree anyway before `git init`; it
      costs nothing and it is a one-way door.

Two things this surfaced that the doc had wrong:

- **`GREENPT_API_KEY` was briefly read by nothing here** — `vision.py` was its
      only reader and is parked — and then became required again, because the
      provider block moved into this repo's `agent/opencode.json` so a checkout
      knows its own models. `server/models.py` reads it too. It is the one
      secret in `.env.example`.
- **`analyze-image` was listed as "stays, unverified".** It could not stay:
      `creator_index` was leaving, and analyze-image imports it. "Unverified"
      was too generous — it was already broken.

- [x] **Shipped a `.env.example`** (2026-08-05). One required secret
      (`GREENPT_API_KEY`), `PUBLIC_URL` once it is reachable from outside,
      `OPENCODE_SERVER_PASSWORD` as a placeholder because start.sh generates and
      appends it on first run, and `ADMIN_DID` commented out because it is for a
      shell running one job, not for the server. `ACTING_DID` is listed the same
      way and under a heading that says so — the server must not carry an
      identity, because a tool learns whose call it is from the session that
      caused it, and a server-wide default would make every user's call look
      like one person's.
- [x] **`public/chat.html` removed from this repo.** The reader is a separate
      project and stays one — see below. It had already diverged from the
      deployed copy by 162 lines, so the drift this was meant to prevent had
      happened before the decision was taken.

## B. Users — atproto OAuth, no app passwords

**Decided: users log in, they do not hand over a password.** `johan.aligned.click`
enrols through the same door as everybody else, and there is no privileged
account with a shortcut. That is the right call for a reason worth stating: an
app password is a bearer credential with full write access to someone's repo,
it cannot be scoped, and a service that collects them is asking people to trust
it in a way it has not earned.

This is the largest item in the release and the most likely to slip the date.

**What it deletes.** The `BSKY_*` identity — the one account every tool
currently reads as. `tools/auth.py`'s app-password machinery survives, but only
to hold the admin fallback below.

**Reads go as the user, with an admin fallback.** An earlier draft of this doc
claimed the reading tools need no token because every `app.bsky.*` call is a
public read. **That is false**, and it is false for exactly the tools that
matter most. Measured unauthenticated against `public.api.bsky.app`,
2026-08-03:

    searchActors    200      getPostThread   200      getFollows     200
    getProfile      200      getPosts        200      getFollowers   200
    getAuthorFeed   200      getLikes        200      getRepostedBy  200

    searchPosts     403  — an HTML Cloudflare block page, not even a JSON error.
                           401 against bsky.social. `search-posts` is the tool
                           the agent reaches for most.
    getActorLikes   400  — "Profile not found" for every actor, handle or DID.
                           An actor's likes are not a public view. This is
                           `liked-posts`.

So: **reads authenticate as the requesting user**, through their PDS with their
OAuth token (the PDS proxies `app.bsky.*` to the appview — the same path
publishing already takes). **The admin app-password session stays as the
fallback**, so `ADMIN_HANDLE` / `ADMIN_APP_PASSWORD` remain in `.env` and
`tools/auth.py` keeps its app-password path for that one account. Only `BSKY_*`
goes away.

- [x] **`tools/bsky.py` points at the sidecar, 2026-08-03.** Every read now
      names a DID and goes to `/xrpc/`. What went with it: the bearer token,
      the `-K -` stdin config that kept it out of argv, and curl itself — which
      was only there because Cloudflare rejects Python's TLS, and this talks to
      127.0.0.1. **No Python here handles a credential any more.**

      Verified with real tools: `search-posts`, `search-actors` and `profile`
      all return results as `johan.aligned.click`. And all four failure paths
      say something actionable — no `ACTING_DID`, a handle where a DID belongs,
      a DID that never logged in, and the sidecar being down.
- [x] **A tool's identity comes from the session, 2026-08-03.** This was the
      last single-user assumption, and it was a quiet one: a tool subprocess
      inherited `ACTING_DID` from whoever started the server, so with two users
      every call would have read as the operator — answering one person's
      question through another person's view of the network, blocks and mutes
      included, and attributing anything published to the wrong repo.

      The link already existed. opencode hands each wrapper a `sessionID`; the
      13 wrappers now pass it down as `ACTING_SESSION`, and `acting_did()` looks
      up the owner the proxy recorded at login. **`start.sh` exports no identity
      at all** — verified by reading the running opencode process's environment
      — and a live `search-posts` over the tunnel still worked, which it could
      only do through the session.

      Checked: a session nobody owns fails loudly rather than falling back, and
      a session **overrides** a conflicting `ACTING_DID`. `ACTING_DID` survives
      only for running a tool by hand from a shell, where there is no session to
      belong to.
- [ ] **Know what reading-as-the-user changes.** Results become viewer-scoped:
      blocks, mutes and moderation prefs apply, so two users get different
      answers to the same query and the admin fallback gives a third. That is
      the *right* behaviour — nobody should be shown accounts they blocked —
      but it means a reproduction of someone's session may not reproduce.
- [ ] **The fallback concentrates rate limits on one account.** If it fires
      often, that is a bug in token handling, not a working fallback. Log when
      it triggers and for whom.
### OAuth runs in a Node sidecar — decided 2026-08-03

The earlier instruction here was "do not hand-roll the DPoP proofs, use an
existing atproto OAuth library". **In Python there is no such library.**
Checked, not assumed:

- The official `atproto` SDK (0.0.69) has **zero** OAuth or DPoP code across
  546 modules. It does app-password `createSession` and nothing else.
- `dpop` on PyPI is a GIF generator.
- `@atproto/oauth-client-node` 0.5.1 is the official implementation, published
  2026-07-31 and actively maintained.

So Node goes on the mini-PC and owns the OAuth half. Installed to
`~/.local/lib/node` (v24.18.1, checksum verified, no sudo) so it is one
directory to delete.

**The sidecar is the authenticated request path, not a login helper.** This is
the part worth understanding before building anything, and it was got wrong in
the first sketch of this decision. `OAuthSession` exposes
`fetchHandler(pathname, init)` and **no way to obtain a usable bearer token** —
`getTokenInfo()` returns expiry, scope and subject only. That is inherent to
DPoP: every request carries a proof signed by the key the token is bound to, so
whoever holds the key must be the one making the request. Handing Python "the
token" is not a thing that can happen.

Which settles the layering, and settles it in a nicer place than planned:

    Python proxy — the only thing on the tunnel
      ├── /client-metadata.json, /oauth/*  → sidecar
      ├── /session/*                       → opencode, session→user enforced
      └── the chat UI

    Node sidecar — 127.0.0.1 only, never exposed
      ├── GET  /client-metadata.json
      ├── GET  /oauth/login?handle=…       PAR + PKCE
      ├── GET  /oauth/callback             code → stored session
      └── POST /xrpc/<nsid>  {did, …}      DPoP-signed, as that user

`tools/bsky.py` calls that last route. **No Python code ever sees a token**,
which is a smaller and more auditable surface than threading one through would
have been.

- [x] **Sidecar built and verified end to end, 2026-08-03.** `oauth/` — JSON
      stores, `requestLocalLock`, bound to `127.0.0.1:4098`. A real login as
      `johan.aligned.click` completed against `bsky.social`, and both calls that
      fail unauthenticated now succeed through `/xrpc/` as that DID:
      **`searchPosts` returns results** where it 403s, and **`getActorLikes`
      returns a feed** where it says "Profile not found". That is the whole
      premise of §B, working.
- [x] **Nothing cryptographic was written.** The rule holds: no JWT signature,
      no JWK handling, no nonce loop in our code. Keep it that way — if a
      change here starts signing something, it is going the wrong way.
- [x] **Failure is loud, decided 2026-08-03.** No silent fallback to the admin
      session. A sidecar that is down, or a session that will not restore, is an
      error the caller sees — because degrading quietly turns "your account"
      into "the operator's account" without telling anyone, and the person it
      misleads is the one whose name ends up on the record.

Two things this left standing that are not done:

- [x] **Confidential-client mode works, first try, 2026-08-03.** Verified by
      what the session stored: `authMethod: private_key_jwt, kid: aligned-1`.
      Bluesky fetched the metadata and JWKS from `chat.aligned.click`, checked a
      signed ES256 assertion, and issued a refresh token that will outlive a few
      days — which is the difference between inviting someone and inviting them
      to log in again on Thursday.

      One correction on the way: `alg` was added to the published JWK, since a
      server that infers it *should* work but an authorization server that
      declines reports a bad assertion rather than a missing field. A `use:
      "sig"` went in with it and came straight back out — the library already
      emits `key_ops`, and RFC 7517 requires the two to agree if both appear,
      which "sig" and a `key_ops` listing "encrypt" do not.
- [x] ~~Confidential-client mode is unexercised~~ `PUBLIC_URL`
      switches it on: `private_key_jwt`, an ES256 key generated on first run,
      `jwks_uri` at `/jwks.json`. It cannot be tested until the tunnel exists,
      because the authorization server has to fetch that URL. **Do not invite
      anyone before it is,** — a loopback client is public, and a public
      client's refresh token is short-lived and single-use, so their session
      dies within days.
- [ ] **`private/oauth/sessions.json` is a credential for every account that
      has logged in** — refresh token and the DPoP private key it is bound to.
      Written `0600` under gitignored `private/`. It is the file to think about
      first in any backup, sync or debug-copy decision.
- [ ] **Client metadata is served at
      `https://aligned.click/client-metadata.json`, and that URL *is* the
      `client_id`.** Redirect URI on the same host,
      `https://aligned.click/oauth/callback`. Both are baked into every
      authorization server that has seen a login, so the hostname is settled
      now (§C) rather than discovered later.
- [ ] **A user record**: DID (the identity — never the handle, which moves),
      handle for display, OAuth tokens, and an invite/enabled flag. One JSON
      file is enough at this size, and it is what the proxy reads per request.
- [ ] **The session cookie/token the browser holds is yours, not atproto's.**
      The OAuth tokens stay server-side. Nothing DPoP-bound should ever be in
      `localStorage`.
- [x] **Publishing goes through the sidecar too, 2026-08-03.** `records.py`
      takes a DID rather than an account name; `create`, `put` and `delete` all
      write as whoever logged in. Verified with a real record: created,
      **read back off the public network unauthenticated**, then deleted and
      confirmed gone.
- [x] **`tools/auth.py` is deleted.** With reads and writes both through the
      sidecar, nothing imported it. Gone with it: `createSession`, the
      10-per-24h rate-limit dance, the cached `.session*.json` files, and every
      app password. `BskyError` moved to `bsky.py`.
- [x] **`publish/lexicons.py` names `ADMIN_DID`** and refuses to guess. A
      schema is published by the account owning the authorising domain, and
      that account now logs into the sidecar like anyone else — needed only
      when a schema changes, which should be close to never.
- [x] **`ADMIN_*` is not needed at all** — which was not the plan. It was to
      survive as the read fallback, and then the fallback was cut for being
      dishonest (a quiet read as the operator puts the wrong name on the
      answer). With nothing left to fall back to, and lexicons published by DID
      through the sidecar, the last app password had no job.

      **So there is no app password anywhere in this project.** Not the
      operator's, not a user's. `BSKY_HANDLE`, `BSKY_APP_PASSWORD`,
      `ADMIN_HANDLE` and `ADMIN_APP_PASSWORD` can all come out of `.env` —
      left in place rather than deleted, since that file is yours and those
      credentials may be used elsewhere.
- [ ] **Enrolment is invite-only.** A successful OAuth login for a DID not on
      the list is a polite refusal, not an account.
- [ ] Removing a user: revoke their tokens, drop the record, delete their
      sessions. Write down the commands.

### One shared workspace — decided

All users share one `agent/` directory and one opencode server. **That is only
safe because the agent users get cannot write.** The condition and the decision
have to ship together:

- [x] **The write tools are denied.** `bash`, `edit` and `read` are denied on
      the agent every user gets, verified by reading the resolved rules back
      from opencode's own `GET /agent` rather than from the config that was
      meant to produce them — the last time this was "verified by reading", the
      rule was on an agent no session ever named and `echo diagnostic` executed
      for weeks.
- [x] **`agent_area/` is gone** (2026-08-05). It existed to give opencode a cwd
      that was not the repo root; `agent/` holds the configuration and is that
      cwd now, which also puts `private/` outside the directory opencode calls
      its project.
- [ ] **One user can have a shell, and it is not sandboxed** (2026-08-05).
      `builder` — bash, write, edit — exists for Johan's own use and is
      unreachable for anybody else: an agent must be *named* in the prompt and
      listed on the caller's line in `users.json`. What it is not is confined.
      opencode's `bash` rule matches commands, not paths, so a prompt injection
      carried in a Bluesky post the agent reads can spend that shell, and
      `private/` holds refresh tokens for every account that has logged in. The
      fix is the unix-user split in PLAN.md §9. **Until then: use `builder` on a
      conversation you started, not on one that has been reading strangers.**
- [ ] **opencode sessions are still global to the process.** The proxy owns the
      session→user table and must reject `/session/<id>` for an id the caller
      does not own. Without this, one user reads everyone's conversations by
      changing a path segment — the single most likely v1 breach, and the one
      thing "one area for all users" does not make safe by itself.
- [ ] **No `/media/` route in v1.** Drop it from `serve.py`. It exists to serve
      downloaded Instagram pictures to draft cards, and that whole path leaves
      with `sync/`. Removing the route also removes the only code reaching into
      `private/` from the web surface.
- [ ] **The rule survives the release:** no `.opencode/tools/` wrapper for
      anything in `publish/`. No agent can publish, for any user.

## C. The edge — home PC, reachable, token-gated

- [x] **Auth proxy first, tunnel second** — done in that order. The proxy is what makes the tunnel
      safe; adding it afterwards means there is a window where it wasn't there.
      Do not start the tunnel before the proxy rejects an unauthenticated
      request.
- [x] **Every request carries a session, or gets a 401.** The session comes from
      §B's login — there is no separately issued API token to hand out, because
      an issued token is a second credential system to revoke and a second way
      to be wrong about who someone is. Compare with `hmac.compare_digest`,
      `HttpOnly` `Secure` `SameSite=Lax` cookie, and an expiry.
- [x] **The session cookie is host-only — no `Domain=` attribute.** This
      is the one that will bite. `read.aligned.click` is a sibling subdomain
      **hosted by GitHub Pages**, so a cookie scoped to `.aligned.click` is
      transmitted to GitHub's servers on every single reader page load. A
      host-only cookie goes to `aligned.click` and nowhere else. Setting
      `Domain=aligned.click` because it looks tidier hands your users' sessions
      to a third party.
- [x] **opencode's server password is set, 2026-08-03.** Generated on first run
      and saved to `.env`; the proxy holds it and nothing else does. Direct
      `POST /session` and `GET /event` on 4096 now return 401, so a routing
      mistake in the proxy no longer exposes an unauthenticated agent, and
      nothing else on the machine can talk to opencode either.

      The scheme is **HTTP Basic with the username literally `opencode`** —
      measured, not guessed: an empty username, `admin` and a random one all
      return 401 with the correct password. Worth writing down, because nothing
      documents it and a `Bearer` token or a custom header both fail the same
      silent way.
- [x] **The proxy is the only thing reachable.** opencode
      (`:4096`) and `serve.py` (`:8777`) stay on `127.0.0.1` — `serve.py`'s own
      docstring says it is not what runs on a real host, and that is still true;
      it stays behind the proxy rather than being replaced.

### It runs on the mini-PC — done 2026-08-05

`atproto-server@192.168.86.250`, four systemd services, all `enabled` so they
come back after a reboot. Reached by cloning the public repo from tangled,
writing `.env` by hand and running `sudo deploy/install.sh` once — which was
also the test of whether anybody *else* could stand this up, and it passed on
the real path rather than a rehearsal.

- [x] **Verified from outside with the laptop dark.** Every laptop process
      stopped — proxy, opencode, sidecar, tunnel — and `aligned.click` still
      answers. Ports 4096, 4098 and 8778 are bound to `127.0.0.1`; the tunnel
      is the only way in.
- [x] **Thirteen of thirteen custom tools registered**, which was not a
      formality: the installer pulled opencode **1.18.13** while the wrappers
      pin `@opencode-ai/plugin` **1.16.2**. That gap could have produced an
      agent with no tools and no error, so it is checked by asking opencode
      what it registered rather than by reading the config that should have
      produced it.
- [x] **The three agents resolve correctly there** — `build` and `focused` deny
      `bash` and `edit`, only `builder` allows them.
- [x] **The provider key resolves from `.env`.** The one failure that would
      have looked fine from every angle: all four services green, every turn
      failing at the provider. On the laptop that key comes from `~/.bashrc`,
      so it is not in `.env` at all and copying the file across would have
      omitted it. systemd loads `.env` and never a shell profile.
- [x] **Logins survived the move.** `private/oauth/` and `proxy-sessions.json`
      came across, so the same cookie, the same publish state and the same
      redactions are live on the new machine.
- [ ] **Send a message and publish a turn from the mini-PC.** The last unproven
      path: a real model call and a record write from the new host. Everything
      up to it is verified; this one costs a turn, so it is deliberately left
      for a human to press.
- [x] **Rebooted once — a simulated power cut, 2026-08-05.** All four came
      back on their own. `enabled` means what it says.
- [ ] **A publish failed once with `UND_ERR_SOCKET: other side closed`** on
      `createRecord` to the PDS, surfacing as a 502 in the UI. Intermittent
      rather than broken: two publishes succeeded against one failure, and ten
      consecutive requests to that PDS from the mini-PC all returned 200.
      `reconcile` is idempotent, so pressing publish again finishes the job —
      but the UI says "Could not publish: 502" and does not say *try again*,
      which is the part worth fixing. (IPv6 is unavailable on that machine and
      curl falls back to v4 cleanly; noted in case it turns out to be related.)
### Moving DNS off Namecheap — required, and the riskiest step in the release

Cloudflare Tunnel can only attach a hostname to a zone Cloudflare hosts:
`*.cfargotunnel.com` targets do not resolve otherwise. `aligned.click` is on
`dns1/dns2.registrar-servers.com`, so the nameservers move.

**Two TXT records in this zone are identities.** If `_atproto.johan.aligned.click`
does not come back up, the handle stops resolving to the DID — which breaks the
Bluesky account, the OAuth login built above, and the authorship of everything
already published. This is not a "recreate it later" record.

Full inventory, read from the authoritative servers 2026-08-03:

    aligned.click                 TXT    v=spf1 include:spf.efwd.registrar-servers.com ~all
    aligned.click                 MX     10 eforward1 / 10 eforward2 / 10 eforward3
                                         15 eforward4 / 20 eforward5 .registrar-servers.com
    read.aligned.click            CNAME  circularmachines.github.io
    _atproto.aligned.click        TXT    did=did:plc:kdnkzvtg6nugup477ev22xfa
    _atproto.johan.aligned.click  TXT    did=did:plc:evocjxmi5cps2thb4ya5jcji
    _lexicon.chat.aligned.click   TXT    did=did:plc:kdnkzvtg6nugup477ev22xfa

- [ ] **Recreate all six in Cloudflare *before* switching nameservers**, so the
      zone is already correct when it goes live. Cloudflare's scan usually
      imports them; check each one rather than trusting it.
- [ ] **Set the `_atproto` and `_lexicon` records to DNS-only (grey cloud).**
      Proxying a TXT record is meaningless, but proxying `read` would put
      Cloudflare in front of GitHub Pages, which is a change nobody asked for.
- [ ] **Email forwarding will break, and that is not obvious.** Those MX records
      are Namecheap's free forwarding service, which only works on their
      nameservers. Anything at `@aligned.click` stops arriving the moment the
      zone moves. Cloudflare Email Routing replaces it — free, sets its own MX
      — but it has to be set up and the destination address re-verified.
- [ ] **Verify after the move, from a resolver that never cached the old zone:**
      both `_atproto` TXTs, `_lexicon`, and that `read.aligned.click` still
      serves the reader. Check the handles resolve in a Bluesky client too — a
      TXT that looks right and a handle that resolves are different claims.
- [x] **Cloudflare Tunnel, running** — no inbound port, stable hostname, and
      it survives a router reboot. **The hostname is `aligned.click`**, the
      apex — moved there from `chat.aligned.click` on 2026-08-03, before anyone
      else had enrolled. That timing was the whole point: the `client_id` is a
      URL on this host and is baked into every authorization server that has
      seen a login, so the existing session was rejected with *"Token was not
      issued to this client"* and had to be redone. Free at one user; not free
      later.
- [x] **The apex serves the app; the reader stays a separate host.** Both could
      not live on one name: `read.aligned.click` is GitHub Pages, and the apex
      can point at the tunnel or at Pages, not both. Serving the reader through
      the proxy would have united the names at the cost of the property that
      matters — a published chat stays readable when this machine is off.
- [x] **`chat.aligned.click` still means something, and no longer hosts
      anything.** It remains the authority for the `click.aligned.chat.*` NSIDs
      (an NSID's authority is its own segments reversed), which is why
      `_lexicon.chat.aligned.click` lives there. The stale CNAME now hits the
      tunnel's catch-all 404 — worth deleting in the dashboard so a name that
      resolves to nothing stops inviting questions.
- [x] **One origin for the page and the API, so there is no CORS at all.**
      `start.sh` currently allows `http://localhost:$UI_PORT`. Same origin means
      nothing to allow, no preflight, and no credentialed cross-origin request
      to get subtly wrong. It is also why the host is `chat` rather than `api`:
      this is the address people see in the browser, so it should read as the
      thing they opened, not as its plumbing.
- [ ] **A prompt is not a unit of cost.** The limit counts prompts a day, and
      one prompt can produce a hundred assistant turns: on 2026-08-04 a single
      "show me the post I made" ran to ~100 turns and 1.35M input tokens before
      stopping on its own. opencode's config has no cap on steps per prompt, so
      this needs watching from the proxy — count assistant turns per prompt on
      the event stream and abort the session past a ceiling. Until then a
      looping model spends without limit inside one allowed request.
- [x] **Rate limited per DID** — requests a minute, prompts a day, 429 on
      either. See §D:
      every user's turns run on one GreenPT key. Per-user limits on requests per
      minute and turns per day, enforced in the proxy, plus a request log. Trust
      is why you invited them; it is not a defence against a runaway loop.
- [ ] **Systemd units** for proxy, opencode, serve.py, tunnel. `start.sh` is a
      foreground script with a `trap`; a release runs across reboots.
- [ ] **Test on cellular**, logged in as a second user,
      before telling anyone it works.

## D. The GreenPT proxy — energy per call

Not cosmetic: the argument for this project is that it is measured rather than
asserted, and this is the measurement. From `PLAN.md §7`, all verified.

**One key, yours.** Every user's turns bill to `GREENPT_API_KEY`. Two things
follow and both are release items, not later:

- The rate limit in §C is what stands between an invited friend and your card.
  A trusted user does not protect you from a loop, and a loop is the normal
  failure mode of an agent.
- Per-user attribution stops being a nice readout and becomes the thing that
  tells you *whose* session did it.

- [ ] **The proxy for agent turns is the only way to get `impact`** — opencode
      stores none of it and there is no response hook, because
      `@ai-sdk/openai-compatible` drops unknown top-level fields and the fix
      (`metadataExtractor`) is a function, unreachable from JSON config.
- [ ] **`tools/vision.py` reads `impact` directly** — it calls GreenPT itself,
      so no infrastructure needed. Cheap to add, but it is now the small half:
      the image path is unverified for v1 (§A) and the volume that justified
      doing it first was the Instagram batch, which does not ship.
- [ ] **Forward `Authorization` untouched.** The proxy never holds a key; the
      key stays in opencode's config and never reaches the browser.
- [ ] **Stream through without buffering.** It sits in front of every agent
      call. If it stalls, the agent stalls.
- [ ] **Stamp `sessionID` and agent name** via a `chat.headers` plugin, so
      energy is attributable per session and per user rather than one anonymous
      total.
- [ ] **Know the cost:** the provider `baseURL` lives in
      `~/.config/opencode/opencode.jsonc` and is **global**, so repointing it
      changes every opencode session on the machine.
- [ ] Units, when displaying: energy is **watt-milliseconds** (÷3.6e6 for Wh),
      emissions **µgCO₂e**. Carry the methodology `version` or the numbers stop
      being comparable. There is no water figure and inventing one would be
      exactly the sin this is meant to avoid.

## E. Publishing to atproto

Mostly done. What remains is one DNS record and one path from the UI.

- [x] Lexicons written, published as `com.atproto.lexicon.schema` records.
- [x] `publish/chat.py` — `--publish` is the flag, printing is the default.
- [x] Reader live at `read.aligned.click`, deep links to a session and a turn.
- [x] **`_lexicon.chat.aligned.click` is live** (added 2026-08-03, confirmed
      from 1.1.1.1, 8.8.8.8 and 9.9.9.9). The whole chain resolves:
      `click.aligned.chat.message` → authority `chat.aligned.click` → TXT →
      `did:plc:kdnkz…` → a `com.atproto.lexicon.schema` record with the right
      defs. **The names mean something to anyone now, not just to us.** A first
      check minutes after it was added came back empty from every resolver and
      from one of the two authoritative servers — that was propagation, not a
      mistake, and it was called too early here.
- [x] **Publish from the UI — done, and verified end to end 2026-08-04.** A
      checkbox per turn, a button that publishes the ticked ones, and every turn
      of a published conversation getting a record so a partly-published one has
      visible holes rather than invisible ones. Posting, replying and quoting
      write their result into the conversation and attach it to that turn, so
      the published record carries a strongRef and the reader draws the post.
      Proven from a Eurosky-hosted account — a different PDS for the OAuth
      session, the record writes and the reads — post, publish, and the card
      appearing on read.aligned.click.
- [x] ~~Publish from the UI, not the CLI~~ (was: §B makes this mandatory) A CLI publish authenticates as whoever holds the credentials
      on the box; under OAuth that is nobody. Another user cannot publish by
      asking you to run a command, because their token is the only thing that
      can write to their repo. So the POST endpoint that approves and publishes
      an exchange is the *only* publish path for anyone but you. If it slips,
      v1 ships as a single-user publisher and multi-user read-only — a
      defensible release, but say so in the README rather than half-wiring it.
- [x] **Agent and model are chosen per message** (2026-08-05). A Setup panel by
      the composer, two dropdowns. Both ride on the prompt itself, so nothing is
      global: no restart, no config file written, and two people using this at
      once can be on different ones. `focused` exists because of a measured
      failure, not a preference — thirteen tools plus opencode's built-ins made
      DeepSeek emit its own DSML syntax as prose and loop on it, so an agent
      with four tools is the lever to pull when a good model starts misbehaving.

      **Who may choose what is per user**, as optional `models`, `tools` and
      `agents` lists in `private/users.json`; absent means everything, so
      nobody's access changed when this arrived. Read through the file the proxy
      already re-reads when it moves, so narrowing somebody takes effect on
      their next request rather than at the next restart.

      One asymmetry worth keeping in mind, because it is the half that would
      fail silently: **a model can be refused, but tools have to be imposed.**
      Naming a model is how you get it, so refusing the name is enough. A tool
      the prompt never mentions falls through to `opencode.json`, which switches
      it *on* — so every tool a caller may not use is written in as `false`
      whatever the page sent. The page can narrow; it cannot widen, and it
      cannot widen by staying silent.
- [x] **Redaction — select the words, press Redact.** A model will state
      something wrong about a named person, and without this the only answers
      are publishing it or withholding the whole turn. A covered span is
      replaced by three block characters in the record: fixed width, so the bar
      cannot say how long the name was, and plain text, so a viewer that has
      never heard of this shows a redaction rather than the words. Reversible
      until it is published and reversible after — uncovering rewrites the
      record — because a covered span was never on the network to begin with.

      Two things it is deliberately not:

      - **Not editing.** The page sends the words to remove, never the text to
        publish, and the server checks them against what the model actually
        said. A page that could send replacement text could put sentences in
        the model's mouth under its label, which is the one thing a record of a
        conversation must not allow.
      - **Not a filter on reading.** The words stay in `private/` only because
        every future write of that turn has to remove them again. Nothing
        publishes them, and a stored span that stops matching its turn
        withholds the turn rather than letting the words through.
- [x] **An unpublished conversation has no records at all — changed 2026-08-06.**
      It used to get a session record and a withheld record per turn the moment
      the turn happened, on the argument that the shape of a conversation is
      public and the words are by decision. Reversed. A withheld record carries
      no words but it carries `createdAt`, and a repo full of them is when
      somebody chats, how often, and how long their sessions run — a behavioural
      profile of conversations they never chose to show anyone, with no way to
      change their mind about having had them. That is a strange thing to attach
      to a tool for private exploration, and it sat badly against "default
      private" in §1.

      **Within a published conversation nothing changes**: every turn still gets
      a record, withheld ones included, because that is where the holes are the
      point. The two rules meet at zero — unticking the last published turn takes
      the whole conversation down rather than leaving the placeholders standing,
      since a hole is only honest when it is in something. The button says
      "Take this conversation down" when that is what pressing it will do.

      **Records written under the old rule stay on the network until somebody
      removes them.** A live conversation cleans itself up the next time it
      syncs — the page sends what is live, which is nothing, and that is now a
      take-down — but an abandoned one never takes another turn, so nothing
      would ever reach it. **Done 2026-08-06**: 11 conversations, 32 withheld
      turns and 11 session records, removed with a throwaway script over
      `publish.take_down` run on the mini-PC. Deliberately not committed — it
      runs once and is a trap afterwards, since it reads rkeys out of
      `published.json`, and that file has to be the one the live server keeps.
      Both machines' copies were byte-identical before and were resynced after.

      Confirmed from the PDS rather than from the script's own count: 6 sessions
      and 127 message records left, and **no session with zero published turns**.
      The 21 withheld records that remain all sit inside conversations published
      in part, which is where they belong. Two of those sessions (9 records, all
      published) predate the UI publish path and are in no `published.json` —
      written by `publish/chat.py`. Nothing here can take those down; they are
      fully published, so nothing should.

      Two follow-ups, neither breaking: **the published schema still describes
      the old rule** — `withheld`'s description says every turn gets a record
      when it happens — so `publish/lexicons.py --publish` wants re-running,
      which needs the `ADMIN_DID` account logged into the sidecar. No field
      changed type, was added or became required, so nothing already written
      stops validating. And §1's "default private" is now true of the storage
      and not only of the gesture.

      **Cleared again 2026-08-09, deliberately and completely** — a fresh start
      before drawing attention to the site. 194 records: 133 for
      `johan.aligned.click` (6 sessions, 127 messages) and 61 for
      `testing2345.eurosky.social` (8 sessions, 53 messages). Both repos verified
      empty afterwards by listing their PDS directly, which is the only answer
      worth having.

      **The take-down could not go through `publish.take_down` this time, and
      that is the lesson worth keeping.** It works from `published.json`, and
      that map had drifted: 15 session entries against 4 session rkeys, while
      2 session and 9 message records were live on the network that it did not
      list — the same class as the two `publish/chat.py` sessions above. Driving
      a take-down from the map would have left 11 records published with nothing
      locally remembering they exist. So the throwaway script enumerated
      `com.atproto.repo.listRecords` instead, which is the only authoritative
      answer to what is published, and refused to run unless the handle it was
      given resolved to the DID it was pointed at — two accounts share that map
      and a misaimed delete is not recoverable. `published.json` is now `{}`,
      with a timestamped backup beside it.

      Worth stating because it recurs: the map is a cache of what this server
      did, not a description of what is published. Anything that must be
      complete has to ask the PDS.
- [ ] **Consent is per-publish.** Publishing is irreversible in the way that
      matters: a delete removes your copy, not anyone else's. A user must see
      exactly what goes out. No default-on.
- [x] **The reader is one repo with this again (2026-08-05), and the
      requirement survives.** What had to be true was never "a separate repo" —
      it was *no backend*, and that is unchanged: `reader/` is a static site
      deployed to GitHub Pages by Actions, reading atproto directly. Being in
      the same tree lets the two share what they had been duplicating, which is
      the thing the split was actively costing: the colour tokens were
      byte-identical copies, the redaction bar was written twice on the day it
      was added, and `lexicons/` had already drifted between the two.

      The consequences below still hold word for word. Two new ones:

      - **`reader/` is the whole of what Pages can publish**, so anything both
        sites use has to live inside it — hence `reader/shared/`, which the
        proxy serves at the same `/shared/…` URLs for the chat side.
      - **Pages must be turned off on the old `read.aligned.click` repo before
        this one takes the CNAME.** Two repositories cannot serve one custom
        domain, and the failure mode is the live reader going down.
- [x] ~~**The reader is a separate project, and that is a requirement.**~~ It reads
      handle → DID → PDS → records itself and talks to no backend, so a
      published conversation is readable when the mini-PC is off, rebooting, or
      gone. The service going down must never take reading with it — which is
      most of the argument for publishing to atproto rather than to a database
      here.

      Two consequences to hold on to:

      - **Nothing in the reader may call this server.** Not for energy figures,
        not for counts, not for a "live" badge. The moment it does, it inherits
        this machine's uptime.
      - **`lexicons/` now exists in both repos.** Here it is the source
        `publish/lexicons.py` publishes from; there it is documentation. The
        published `com.atproto.lexicon.schema` records are the authority over
        both, so a mismatch is a bug in whichever copy disagrees with the
        network — not a merge conflict.

## F. Mobile

Verified, not guessed: **there is not one width-based `@media` query in either
frontend.** The only queries present are `prefers-color-scheme` and
`prefers-reduced-motion`. Both pages were built at desktop width and have never
had a breakpoint.

Chat (`public/index.html`, this repo) and reader (`public/chat.html` in the
`aligned.click` repo — one copy now, not two):

- [ ] **Inputs at 14px cause iOS Safari to zoom the page on focus.** `#input`
      and `.compose-text` are both `font-size: 14px`. Anything ≥16px doesn't.
      This is the single worst one — the page jumps every time you tap to type.
- [ ] **`#app { height: 100% }`** fights the mobile URL bar. `100dvh`, with a
      `100vh` fallback.
- [ ] **`.msg { max-width: 82% }`** throws away 13% of a 390px screen. Widen to
      ~92% below 600px; the bubble asymmetry that reads as conversation on a
      wide screen just reads as a narrow column on a phone.
- [ ] **Side padding**: 16px on `header`, `#log` and `#composer` leaves 358px
      usable at 390px. 10–12px below 600px.
- [ ] **Cards.** `.msg.has-embed` is `width: 420px` and `atproto-post` is
      `width: 480px`, both with `max-width: 100%` so they clamp — but the
      `atproto-wc` components have their own internals. Check a real post card
      and a real profile card at 360px before calling this done.
- [ ] **Hover does not exist on touch.** `.card-tab:hover`, `header
      button:hover`, `#send` states — and, importantly, the disabled action
      buttons explain themselves with `title="Not connected"`, a tooltip that
      **never appears on a phone**. On touch those buttons are unexplained. Give
      them a visible label or make the explanation a tap.
- [ ] **Composer with the keyboard up**: sticky bottom, `env(safe-area-inset-
      bottom)`, and the log must still scroll to the newest message.
- [ ] **Tap targets** — the card tabs are small. 44px minimum.
- [ ] **Reader deep links** (`#m-<rkey>`) must still scroll to the right turn
      after the live cards load and reflow the page.
- [ ] Test on a real phone over the tunnel, not in devtools. Both pages.

## G. Other people's data — out of scope, and here is why

Empty by construction, not by omission. `sync/`, `private/external.db` and
everything the strategizer collected **stay off the mini-PC entirely**. The
service holds no data about anyone who did not log into it, so the retention
work in `PLAN.md` (`purge.py`, the subjects table, the scrape allowlist) is not
a v1 blocker — it is a blocker for the strategizer, on a different machine, on
a different day.

Two things do carry over, and they are small:

- [x] **Nothing copies the strategizer's databases onto it** (held, 2026-08-05).
      When `private/` was moved to the mini-PC it was copied *file by file* —
      `users.json`, `waitlist.json`, `published.json`, `proxy-sessions.json` and
      `oauth/` — and not as a directory. `strategist/`, `fetches/`
      (the scraped LinkedIn and Instagram material), `creators.json`,
      `analysis.db`, `external.db` and `NOTES.md` stayed on the laptop.
      `rsync private/` would have been one word shorter and would have put all
      of it on the server. The moment any of it lands there this section stops
      being empty and `purge.py` becomes overdue again.
- [ ] **Back up the user record.** It is OAuth tokens and DIDs for real people,
      on one PC in a house. Losing it means everyone re-enrols; leaking it is
      worse.

---

## Ship sequence

1. **§A — clean the tree, then `git init`.** First, because it is the only step
   that cannot be undone, and because everything after it is easier in a tree
   with the strategizer gone.
2. **§C's hostname — decided: `aligned.click`.** The tunnel itself can come
   later; the name could not, because §B's OAuth `client_id` is a URL on it.
3. **§B — OAuth, still on localhost.** This is the long pole; if the date is at
   risk, this is what is at risk. Do the `bsky.py` token-threading as part of
   it, not before — there is no useful intermediate state now that reads need
   an identity.
4. **§F — mobile.** Self-contained and testable from a phone on the LAN, so it
   can run in parallel with §B rather than behind it.
5. **§C — proxy, verified rejecting an unauthenticated request and a
   cross-user session id, *then* the tunnel.**
6. **§E — the DNS TXT, then the publish endpoint.**
7. **§D — the energy proxy.** It can follow the release; the *rate limit* in §C
   cannot.
8. Cellular test as a second user. Then invite one person who isn't you.

### The remotes, at step 1 — tangled canonical, GitHub a mirror

Set after `git init`, not before: this tree still points at `at_opencode`, which
is the repository being left behind. One `git push` should reach both, so the
mirror cannot quietly fall behind the thing it mirrors.

    git init && git add -A && git commit -m "aligned.click v1"
    git remote add origin <tangled-url>          # fetch and push
    git remote set-url --add --push origin <tangled-url>
    git remote set-url --add --push origin git@github.com:circularmachines/aligned.click.git
    git push -u origin main

`git remote -v` should then show one fetch URL (tangled) and two push URLs.
Fetching from GitHub is never right: it is a copy, and a divergence there is a
mistake to overwrite rather than merge.

**GitHub is a mirror for one reason — Pages.** `reader/` is deployed by
`.github/workflows/pages.yml`, which only runs on GitHub, so the mirror is what
keeps read.aligned.click alive. Two things have to be done there by hand:

- [ ] **Repository settings → Pages → Source: GitHub Actions.** Without it the
      workflow uploads an artifact nothing deploys.
- [ ] **Turn Pages off on the old `read.aligned.click` repository first.** Two
      repositories cannot serve one custom domain — `reader/CNAME` claims
      `read.aligned.click`, and GitHub will refuse the second claim. Doing it in
      the other order takes the live reader down rather than moving it.
- [ ] **Then check the reader actually redeployed** from this repo, rather than
      assuming the CNAME moved. It is a static site with no backend, so the
      failure is silent: the old copy keeps serving until DNS and Pages agree.

## Explicitly not in v1

Say these in the README so nobody discovers them:

- **No agent writes to Bluesky.** Every action button in a card is inert; the
  only path from the UI to the agent is the composer. Publishing a conversation
  is a separate, human-approved act.
- **The agent cannot write files or run commands.** That is what makes one
  shared workspace acceptable, so it is a guarantee, not a default.
- **No app passwords from users.** The service never asks a user for one and
  never stores one. The operator's own credential exists as a read fallback and
  can write to exactly one repo: the operator's.
- No background workers, no notes, no delegation.
- No strategizer, no scraping, no imports, no `/media/`.
- No appview: the member list is a curated list, because `listRecords` names one
  repo and cross-author listing needs an index. **Since 2026-08-09 that list is
  itself on atproto** — one `click.aligned.chat.member` record per member in the
  collective's repo, replacing `reader/authors.json`, so admitting somebody
  takes effect without a commit and the reader still calls nothing here.
- No account recovery, no self-signup. Invite only, and identity is atproto's
  problem rather than ours — which is most of the point.
- The left pane, the matcher, the confirm loop, `analyze-video` — all in
  `PLAN.md`, none in this release.

## Open — deliberately undecided

Two questions that are not blockers but will be answered by shipping something,
so record the options rather than defaulting into one by accident.

### 1. Private vs. public chats

Right now every conversation is private (it lives in opencode's local storage)
and publishing is a separate, explicit act. The question is whether that stays
true, and what the gesture for publishing is.

**The proposal on the table:** the send button *is* the publish button — sending
publishes the user's message and the preceding assistant message to atproto.
Held open. What recommends it, and what makes it uncomfortable:

- It makes publishing continuous rather than a decision, which matches how a
  conversation actually reads — you approve the exchange you just had, while
  you remember it, instead of reviewing a transcript later.
- It makes the transcript *authored*: a user who knows the last exchange goes
  public writes differently. Whether that is a feature or a chilling effect
  depends entirely on whether they can opt out mid-conversation, cheaply.
- **The asymmetry is the problem.** You approve the assistant's last message
  before you have seen what your own message causes. So the model's reply to
  the message you are sending *now* is published by your *next* send — which
  means the last exchange of every conversation is never published, and a
  conversation you walk away from ends mid-sentence in public.
- It removes the "publish a session" concept entirely, and with it any way to
  publish something that already happened.

Alternatives worth costing before choosing: a per-conversation public/private
toggle set at the start; a per-message "publish this exchange" affordance that
is *not* the send button; publish-at-the-end with a review screen (what
`publish/chat.py` does today, moved into the UI).

Whatever wins, two things hold: **default private**, and **a user sees exactly
what goes out before it goes**, because a record on the firehose cannot be
recalled.

### 2. Showing energy in the UI

§D captures the number. Where it surfaces is unanswered, and the answer
determines whether it is an honest measurement or decoration.

The options run from a per-turn figure (accurate, and noise at 0.016 Wh for a
short reply), through a session total (readable, and the natural unit since it
matches what a published conversation *is*), to a running account total (the
credible number for the project's argument, and the one nobody looks at).

Two things to get right whenever it lands: **units people can hold** — 0.57 Wh
means nothing to most readers, and a comparison invites the accusation of
spin, so pick carefully — and **the number must be the measurement, not a
model of it**. Carry GreenPT's methodology `version`, and say there is no water
figure rather than estimating one.

Worth noting the interaction with §1: if a published record carried its energy
cost, that would be the first version of this anyone else could verify. That is
a lexicon change, so it is a v2 conversation, but it is the reason not to paint
this into a corner now.

## Known-imperfect at ship

Write these down here rather than discovering them in an issue:

- An edit in a card is invisible to the agent and does not survive a reload.
  Cards are rebuilt from tool output in the message history.
- **Publishing is silent.** A `click.aligned.chat.*` record lands in the user's
  repo, goes out on the firehose and is readable by anyone — but no Bluesky
  notification fires, it appears in nobody's feed, and no follower learns it
  exists. Custom records are invisible to the appview, which only indexes
  `app.bsky.*`. So a user who publishes a conversation and expects a response
  gets silence, and will reasonably conclude the feature is broken. The answer
  is the `discussion` field: post about it on Bluesky, where attention already
  is, and link the two. Make sure the UI says this at the moment someone
  publishes, not in a README they won't read.
- A referenced post that its author later deletes stops appearing in the
  conversation. That is correct behaviour, and it does make old logs read worse.
- `read.aligned.click/` (bare root) may still serve a stale 404 from GitHub's
  edge; `/chat.html` and `/index.html` are fine and are what links use.
