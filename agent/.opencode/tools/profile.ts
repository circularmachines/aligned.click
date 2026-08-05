import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/profile.py — located via the git worktree.
export default tool({
  description:
    "Get Bluesky profile metadata for one or more accounts (up to 25): " +
    "follower / following / post counts and bio. This is the node data for " +
    "social-graph work — use it to size up or verify an account. Returns one " +
    "line per account: `@handle (Name) — did · N followers / M following / K " +
    "posts · bio`. Accounts are referenced by @handle (feed them to " +
    "author-posts, follows, etc.).",
  args: {
    actors: tool.schema
      .array(tool.schema.string())
      .describe('Handles or DIDs, e.g. ["alice.bsky.social", "bob.bsky.social"]'),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/profile.py`
    const actors = (Array.isArray(args.actors) ? args.actors : [String(args.actors ?? "")])
      .map((a) => String(a).trim())
      .filter(Boolean)
    if (actors.length === 0) return "profile: no accounts given"
    return await $`python3 ${script} ${actors}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
