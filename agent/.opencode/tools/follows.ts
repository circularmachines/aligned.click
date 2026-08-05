import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/follows.py — located via the git worktree.
export default tool({
  description:
    "List the accounts a Bluesky user follows (walks the follow graph " +
    "outward). Returns one line per account: `@handle (Name) — did · bio`. " +
    "Use it to see who someone follows, then explore those accounts.",
  args: {
    actor: tool.schema.string().describe("Handle or DID whose follows to list"),
    limit: tool.schema.number().describe("Max accounts to return").default(50),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/follows.py`
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 50
    return await $`python3 ${script} ${args.actor} --limit ${String(limit)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
