import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/search_actors.py — located via the git worktree so
// there are no hardcoded paths. The Python side handles Bluesky auth and the
// Cloudflare-friendly curl transport.
export default tool({
  description:
    "Search Bluesky accounts by name, handle, or bio text. Returns one line " +
    "per account: `@handle (Name) — did · counts · bio`. Bios are searched " +
    "too, so a topic ('permaculture') finds people who describe themselves " +
    "that way, not just accounts named after it. Use it to find who is " +
    "already on Bluesky in a subject area.",
  args: {
    query: tool.schema.string().describe("A name, handle, or bio term"),
    limit: tool.schema.number().describe("Max accounts to return").default(25),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/search_actors.py`
    // Guard limit — the model sometimes omits it and a schema default doesn't
    // always reach here, which would send the literal "undefined" (argparse
    // exit 2).
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 25
    return await $`python3 ${script} ${args.query} --limit ${String(limit)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
