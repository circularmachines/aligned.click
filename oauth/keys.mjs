// The client's signing key, for confidential-client authentication.
//
// atproto distinguishes confidential clients (which authenticate to the
// authorization server with a signed assertion) from public ones (which do
// not). The difference is not ceremony: a public client's refresh token is
// short-lived and single-use, so a public-client session dies within days. A
// confidential client's survives, which is the difference between "log in
// once" and "log in again every time you open it".
//
// So we hold a private key. It never leaves this process; the authorization
// server fetches the *public* half from `jwks_uri` and uses it to check the
// assertion. The private half is written 0600 under private/ and is, along
// with sessions.json, one of the two files here that matter.
//
// Rotating it invalidates nothing immediately — sessions already issued keep
// working until they refresh — but it does mean the AS must re-fetch the JWKS.
import { chmodSync, existsSync, readFileSync, writeFileSync } from "node:fs"
import { JoseKey } from "@atproto/oauth-client-node"

export async function loadOrCreateKey(path) {
  if (existsSync(path)) {
    return JoseKey.fromImportable(JSON.parse(readFileSync(path, "utf8")))
  }
  // The kid is stable and arbitrary. It has to be *a* name, because a JWKS is
  // a set and the assertion header says which member signed it.
  const key = await JoseKey.generate(["ES256"], "aligned-1")
  writeFileSync(path, JSON.stringify(key.privateJwk, null, 2), { mode: 0o600 })
  chmodSync(path, 0o600)
  return key
}
