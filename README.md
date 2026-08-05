# aligned.click

An agent that reads Bluesky with you and publishes the conversations you choose
to publish, as records in **your** atproto repo. Served at
**https://aligned.click** from a mini-PC. No framework and no build step.

Invite-only: a successful login by somebody not on the list joins a waitlist
rather than becoming an account.

The reader that renders published conversations lives in `reader/` and is
deployed to GitHub Pages as **read.aligned.click**. It is in this repo but not
behind this server: it reads atproto directly and calls nothing here, so a
published conversation stays readable when this machine is off, rebooting, or
gone. That is most of the argument for publishing to atproto rather than to a
database, and **nothing in `reader/` may ever call this server** — not for
energy figures, not for counts, not for a "live" badge.

See `RELEASE.md` for what v1 is and what is still open, `PLAN.md` for why things
are the way they are, and `deploy/` for running it on a server.

## Run it

```
./start.sh
```

Then open http://127.0.0.1:8778. Four processes, and Ctrl-C stops all of them:

| | |
|---|---|
| `oauth/server.mjs` (4098) | the OAuth sidecar — the only thing holding atproto tokens |
| `opencode serve` (4096) | the agent, started from `agent/` |
| `server/proxy.py` (8778) | the auth proxy, which serves the UI and everything else |
| `cloudflared` | the tunnel, if `PUBLIC_URL` is set |

Everything except the tunnel binds `127.0.0.1`.

## How it works

**The proxy is the only thing that is ever exposed, and the only thing that
knows who anyone is.** Three jobs, in order of how badly each fails:

1. **Authenticate.** A cookie names a session, a session names a DID, and a DID
   is either on the invite list or is not.
2. **Enforce session ownership.** opencode has no concept of a user — its
   sessions are global to the process, so `/session/<id>/…` for somebody else's
   id would simply work. The proxy owns the map from session to DID, and that
   map is the whole of multi-user isolation.
3. **Filter the event stream.** `GET /event` is a *single global SSE stream*, so
   a client with no filter sees other people's message deltas. Events are
   filtered here, fail-closed.

`public/index.html` is a single self-contained page. It opens a session, sends
prompts to `POST /session/{id}/prompt_async` (which returns 204 — the reply is
not in the response) and reads the reply off one persistent `EventSource` on
`GET /event`. The message id is left for the server to assign; sending our own
wedges every turn after the first.

`?server=` points the page at a **different proxy**, never at opencode: talking
straight to opencode would skip authentication, session ownership and the event
filter in one step.

## Layout

| | |
|---|---|
| `reader/` | read.aligned.click — a static site, deployed by GitHub Actions, with no backend |
| `reader/shared/` | what both sites use: the vendored libraries, the colour tokens, the redaction bar. Inside `reader/` because Pages can only publish one tree; the proxy serves the same files at the same `/shared/…` URLs |
| `agent/` | everything the agent is configured by — `opencode.json`, `OPERATING.md`, `AGENTS.md`, `models/`, and the `.opencode/tools/` wrappers. opencode runs from here, so `private/` is outside its project |
| `tools/` | the Bluesky tools themselves, in Python. Read-only; they hold no credentials and call the sidecar |
| `server/` | the proxy, and the write paths — publishing, posting, redaction. **No tool wrapper may ever exist for anything here**: the agent proposes, a person presses |
| `publish/` | the record writers and the lexicons' source |
| `oauth/` | the OAuth sidecar. DPoP binds a token to a key, so this is the authenticated request path, not a login helper |
| `private/` | untracked, and holds every user's refresh tokens. Nothing in the repo may read it into the agent's reach |

## Notes

- No page loads anything from a CDN. The libraries are in `reader/shared/`,
  and a CSP (a header from the proxy, a meta tag on Pages) means a script tag
  pointing anywhere else will not load — these pages can post as you.
- Don't fetch `/config/providers` from the browser — unlike `/provider`, it
  returns provider API keys in the clear.
- Model and agent are chosen per message from the UI's Setup panel. Who may
  choose what is set per user in `private/users.json`.
