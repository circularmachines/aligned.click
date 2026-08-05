// The OAuth sidecar: the only process that holds a user's credential, and the
// only JavaScript in this project.
//
// It exists because atproto OAuth binds every access token to a key with DPoP —
// each request carries a fresh proof signed by that key — so *whoever holds the
// key must be the one making the request*. There is no bearer token to hand to
// Python. That is why this is not a login helper that returns a token: it is
// the authenticated request path. Python asks it to make a call as a DID; it
// makes the call.
//
// It is also why this is in Node at all. There is no atproto OAuth library for
// Python — the official SDK has no OAuth code, and `dpop` on PyPI is a GIF
// generator — and the one part of a release that should never be hand-written
// is the part that signs things. @atproto/oauth-client-node does PAR, PKCE,
// DPoP, nonce retries and refresh. Nothing here signs anything itself, and if
// a change to this file starts to, it is going the wrong way.
//
//     GET  /health                     is it up, and as what
//     GET  /client-metadata.json       the client_id document (public mode)
//     GET  /jwks.json                  the public half of the signing key
//     GET  /oauth/login?handle=        302 to the user's own server
//     GET  /oauth/callback             code -> a stored session
//     GET  /oauth/sessions             which DIDs are logged in
//     POST /xrpc/<nsid>                one call, as one DID
//
// Binds 127.0.0.1 and nothing else. It is reached through the Python proxy,
// which is the only thing on the tunnel.
import { createServer } from "node:http"
import { join } from "node:path"
import { NodeOAuthClient } from "@atproto/oauth-client-node"
import { requestLocalLock } from "@atproto/oauth-client"
import { loadOrCreateKey } from "./keys.mjs"
import { jsonStore } from "./store.mjs"

const PORT = Number(process.env.OAUTH_PORT || 4098)
const STORE_DIR = process.env.OAUTH_STORE_DIR || join(import.meta.dirname, "..", "private", "oauth")
// Set once the tunnel exists. Absent means loopback development, which is a
// different kind of client — see below.
const PUBLIC_URL = process.env.PUBLIC_URL?.replace(/\/$/, "")
// Where the browser comes back to. **Not this process.** The redirect has to
// land on the auth proxy, because that is the origin the person is actually
// using and the only thing that can set their cookie; a callback that arrived
// here would complete the login and leave the browser with nothing to show for
// it. In production it is the public URL; in development, the proxy on
// loopback — which a `http://localhost` client_id is allowed to name.
const PROXY_URL = (process.env.PROXY_URL || "http://127.0.0.1:8778").replace(/\/$/, "")
const SCOPE = "atproto transition:generic"

const stateStore = jsonStore(join(STORE_DIR, "state.json"))
const sessionStore = jsonStore(join(STORE_DIR, "sessions.json"))

// Two client shapes, because loopback and production are genuinely different
// clients rather than one client configured twice.
//
// In production the client_id is a URL the authorization server fetches, and we
// are a *confidential* client: we authenticate with a signed assertion, which
// is what buys a refresh token that lives longer than a few days.
//
// In development there is no public URL to fetch, so atproto's loopback form is
// used: `http://localhost` with the redirect and scope as query parameters, and
// the server synthesises the metadata. A loopback client cannot be confidential
// — there is nowhere to serve a JWKS from — so dev sessions are shorter-lived
// than real ones. That is a property of the development mode, not a bug to fix.
const isProduction = Boolean(PUBLIC_URL)
const redirectUri = isProduction ? `${PUBLIC_URL}/oauth/callback` : `${PROXY_URL}/oauth/callback`

const key = isProduction ? await loadOrCreateKey(join(STORE_DIR, "client-key.json")) : null

const clientMetadata = isProduction
  ? {
      client_id: `${PUBLIC_URL}/client-metadata.json`,
      client_name: "aligned.click",
      client_uri: PUBLIC_URL,
      redirect_uris: [redirectUri],
      scope: SCOPE,
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
      application_type: "web",
      token_endpoint_auth_method: "private_key_jwt",
      token_endpoint_auth_signing_alg: "ES256",
      dpop_bound_access_tokens: true,
      jwks_uri: `${PUBLIC_URL}/jwks.json`,
    }
  : {
      client_id:
        `http://localhost?redirect_uri=${encodeURIComponent(redirectUri)}` +
        `&scope=${encodeURIComponent(SCOPE)}`,
      client_name: "aligned.click (development)",
      redirect_uris: [redirectUri],
      scope: SCOPE,
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
      application_type: "native",
      token_endpoint_auth_method: "none",
      dpop_bound_access_tokens: true,
    }

const client = new NodeOAuthClient({
  clientMetadata,
  keyset: key ? [key] : undefined,
  stateStore,
  sessionStore,
  // Resolves a handle to a DID before we know which server to talk to. It is
  // the first network call of a login and the first thing to fail on a typo.
  handleResolver: "https://bsky.social",
  // Serialises token refreshes. Without it the library warns, and it is right
  // to: two concurrent refreshes of one session race, and a refresh token is
  // single-use — the loser's is already spent, so the session is revoked. This
  // is the in-process lock, which is correct because there is exactly one of
  // these processes. A second one would need a real lock, not this.
  requestLock: requestLocalLock,
})

const send = (res, status, body, type = "application/json") => {
  const text = type === "application/json" ? JSON.stringify(body, null, 2) : String(body)
  res.writeHead(status, { "content-type": type, "content-length": Buffer.byteLength(text) })
  res.end(text)
}

const readBody = (req) =>
  new Promise((resolve, reject) => {
    let data = ""
    req.on("data", (chunk) => {
      data += chunk
      if (data.length > 1e6) reject(new Error("body too large"))
    })
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {})
      } catch {
        reject(new Error("body is not JSON"))
      }
    })
    req.on("error", reject)
  })

const routes = {
  "GET /health": async () => ({
    ok: true,
    mode: isProduction ? "production" : "loopback",
    client_id: clientMetadata.client_id,
    confidential: Boolean(key),
    sessions: (await sessionStore.keys()).length,
  }),

  "GET /client-metadata.json": async () => {
    if (!isProduction) throw httpError(404, "no client metadata in loopback mode — the client_id carries it")
    return clientMetadata
  },

  "GET /jwks.json": async () => {
    if (!key) throw httpError(404, "no signing key in loopback mode")
    // `alg` is stated rather than left to be inferred. A P-256 key can only
    // sign ES256, so every server *should* work it out — but "should" is doing
    // real work in that sentence, and an authorization server that declines the
    // client assertion gives an error about the assertion, not about a missing
    // field in a document it fetched minutes earlier.
    // Only `alg` is added. A `use: "sig"` was here briefly and was wrong: the
    // library already emits `key_ops`, and RFC 7517 requires the two to agree
    // if both appear — which "sig" and a key_ops listing "encrypt" do not.
    return { keys: [{ ...key.publicJwk, alg: "ES256" }] }
  },

  "GET /oauth/login": async (url, _req, res) => {
    const handle = url.searchParams.get("handle")
    if (!handle) throw httpError(400, "?handle= is required")
    // This does the work: resolves the handle, discovers the authorization
    // server, and pushes the request (PAR) before returning somewhere to go.
    const authorizeUrl = await client.authorize(handle, { scope: SCOPE })
    if (url.searchParams.get("json") === "1") return { authorize: authorizeUrl.toString() }
    res.writeHead(302, { location: authorizeUrl.toString() })
    res.end()
    return null
  },

  "GET /oauth/callback": async (url) => {
    const { session } = await client.callback(url.searchParams)
    return { did: session.did, message: "logged in — this window can be closed" }
  },

  "GET /oauth/sessions": async () => ({ dids: await sessionStore.keys() }),

  "GET /oauth/logout": async (url) => {
    const did = url.searchParams.get("did")
    if (!did) throw httpError(400, "?did= is required")
    const session = await client.restore(did)
    await session.signOut()
    return { did, signedOut: true }
  },
}

// One XRPC call, as one DID. The pathname and query go straight through, so
// this stays a transport rather than a second copy of the Bluesky API — every
// tool that used to call bsky.social calls here instead, unchanged otherwise.
async function xrpc(url, req, res) {
  const nsid = url.pathname.slice("/xrpc/".length)
  const did = url.searchParams.get("did")
  if (!did) throw httpError(400, "?did= is required — a call is made as somebody")
  if (!nsid) throw httpError(400, "no method named")

  // Distinguish "never logged in" from "logged in, session no longer usable".
  // The library reports a missing session as "deleted by another process",
  // which sends someone looking for a race that did not happen. The two have
  // completely different fixes: log in, versus find out what revoked it.
  if (!(await sessionStore.get(did))) {
    throw httpError(401, `${did} has not logged in — no session was ever stored for it`)
  }
  let session
  try {
    session = await client.restore(did)
  } catch (err) {
    throw httpError(401, `session for ${did} is no longer usable (${err.message}) — log in again`)
  }

  const init = { method: req.method, headers: {} }
  if (req.method === "POST") {
    const body = await readBody(req)
    init.body = JSON.stringify(body)
    init.headers["content-type"] = "application/json"
  }
  const query = new URLSearchParams(url.searchParams)
  query.delete("did")
  const path = `/xrpc/${nsid}${query.size ? `?${query}` : ""}`

  const upstream = await session.fetchHandler(path, init)
  const text = await upstream.text()
  res.writeHead(upstream.status, {
    "content-type": upstream.headers.get("content-type") || "application/json",
    "content-length": Buffer.byteLength(text),
  })
  res.end(text)
  return null
}

function httpError(status, message) {
  const err = new Error(message)
  err.status = status
  return err
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`)
  try {
    if (url.pathname.startsWith("/xrpc/")) {
      await xrpc(url, req, res)
      return
    }
    const handler = routes[`${req.method} ${url.pathname}`]
    if (!handler) return send(res, 404, { error: "no such route", path: url.pathname })
    const body = await handler(url, req, res)
    if (body !== null) send(res, 200, body)
  } catch (err) {
    const status = err.status || 500
    // The message, not the stack. These are read by a Python tool and end up in
    // whatever the model sees, and a stack trace there is noise at best.
    send(res, status, { error: err.constructor.name, message: err.message })
    if (status >= 500) console.error(`[oauth] ${req.method} ${url.pathname}`, err)
  }
})

server.listen(PORT, "127.0.0.1", () => {
  console.log(
    `oauth sidecar:   http://127.0.0.1:${PORT}  ` +
      `(${isProduction ? "production, confidential" : "loopback development"})`,
  )
  console.log(`  client_id:     ${clientMetadata.client_id}`)
  console.log(`  store:         ${STORE_DIR}`)
})
