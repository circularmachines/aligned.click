import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/author_posts.py — located via the git worktree so
// there are no hardcoded paths. The Python side handles Bluesky auth, the
// Cloudflare-friendly curl transport, and the stable [N] index assignment.
export default tool({
  description:
    "Fetch a Bluesky user's recent posts. Returns one line per post: " +
    "`[N] @handle (K likes) at://uri — preview`. To show a post in your reply, " +
    "write just its bracketed index like [N]; the UI renders it as a live card.",
  args: {
    actor: tool.schema.string().describe("Handle, e.g. 'alice.bsky.social'"),
    limit: tool.schema.number().describe("Max posts to return").default(10),
    replies: tool.schema.boolean().describe("Include replies").default(false),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/author_posts.py`
    // Guard limit — the model sometimes omits it and a schema default doesn't
    // always reach here, which would send the literal "undefined" (argparse
    // exit 2).
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 10
    const flags = args.replies ? ["--replies"] : []
    return await $`python3 ${script} ${args.actor} --limit ${String(limit)} ${flags}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
