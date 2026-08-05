import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/liked_posts.py — located via the git worktree.
// Bluesky serves a repo's likes to its owner only, so this works for the
// logged-in account; any other handle comes back as an error from the Python side.
export default tool({
  description:
    "Fetch the posts an account has liked — the inverse of liked-by, which " +
    "returns the accounts that liked one post. Only works for the logged-in " +
    "account. Returns one line per post: `[N] @handle (K likes) at://uri — " +
    "preview`. To show a post in your reply, write just its bracketed index " +
    "like [N]; the UI renders it as a live card.",
  args: {
    actor: tool.schema.string().describe("Handle, e.g. 'alice.bsky.social'"),
    limit: tool.schema.number().describe("Max posts to return").default(10),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/liked_posts.py`
    // Guard limit — the model sometimes omits it and a schema default doesn't
    // always reach here, which would send the literal "undefined" (argparse
    // exit 2).
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 10
    return await $`python3 ${script} ${args.actor} --limit ${String(limit)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
