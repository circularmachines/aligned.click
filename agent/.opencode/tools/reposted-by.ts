import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/reposted_by.py — located via the git worktree.
export default tool({
  description:
    "List the accounts that reposted a specific post (walks the engagement " +
    "graph). Pass the post's at:// URI. Returns one line per account: " +
    "`@handle (Name) — did · bio`. Reposts are a strong signal of who " +
    "amplified a post — useful for tracing how something spread.",
  args: {
    uri: tool.schema.string().describe("at:// URI of the post"),
    limit: tool.schema.number().describe("Max accounts to return").default(50),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/reposted_by.py`
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 50
    return await $`python3 ${script} ${args.uri} --limit ${String(limit)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
