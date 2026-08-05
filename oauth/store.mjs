// The two stores @atproto/oauth-client-node needs, backed by one JSON file each.
//
// A SimpleStore is three methods — get, set, del — so this is deliberately
// dull. What it holds is not dull: `sessions.json` contains refresh tokens and
// the private DPoP key each session is bound to. That file is a credential for
// every account that has logged in, which is why it lives under private/ (which
// is gitignored) and is written 0600.
//
// Whole-file rewrites, not appends. At this size the file is a few kilobytes
// and the alternative is a database; the write is atomic via rename, so a crash
// mid-write leaves the previous version rather than half of the new one.
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"

export function jsonStore(path) {
  mkdirSync(dirname(path), { recursive: true })

  const read = () => {
    try {
      return JSON.parse(readFileSync(path, "utf8"))
    } catch (err) {
      // ENOENT is the first run. Anything else is a corrupt file, and silently
      // starting empty would log everyone out without saying why.
      if (err.code === "ENOENT") return {}
      throw new Error(`${path} is unreadable: ${err.message}`)
    }
  }

  const write = (data) => {
    const tmp = `${path}.tmp`
    writeFileSync(tmp, JSON.stringify(data, null, 2), { mode: 0o600 })
    renameSync(tmp, path)
  }

  return {
    async get(key) {
      return read()[key]
    },
    async set(key, value) {
      const data = read()
      data[key] = value
      write(data)
    },
    async del(key) {
      const data = read()
      delete data[key]
      write(data)
    },
    // Not part of SimpleStore — the sidecar's own routes use it to answer
    // "who has logged in", which is the only listing anything needs.
    async keys() {
      return Object.keys(read())
    },
  }
}

export const storePath = (dir, name) => join(dir, name)
