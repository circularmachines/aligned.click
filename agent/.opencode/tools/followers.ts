import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/followers.py — located via the git worktree.
export default tool({
  description:
    "List the accounts that follow a Bluesky user (walks the follow graph " +
    "inward). Returns one line per account: `@handle (Name) — did · bio`. " +
    "Use it to see a user's audience or find who's connected to them.",
  args: {
    actor: tool.schema.string().describe("Handle or DID whose followers to list"),
    limit: tool.schema.number().describe("Max accounts to return").default(50),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/followers.py`
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 50
    return await $`python3 ${script} ${args.actor} --limit ${String(limit)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
