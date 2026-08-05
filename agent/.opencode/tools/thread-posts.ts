import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/thread_posts.py — located via the git worktree so
// there are no hardcoded paths. The Python side handles Bluesky auth, the
// Cloudflare-friendly curl transport, and the stable [N] index assignment.
export default tool({
  description:
    "Fetch a Bluesky post thread (the whole conversation) from a post's " +
    "at:// URI. Returns the ancestors, the focused post (marked ►), and the " +
    "reply tree, one line per post indented by depth: `[N] @handle (K likes) " +
    "at://uri — preview`. To show a post in your reply, write just its " +
    "bracketed index like [N]; the UI renders it as a live card.",
  args: {
    uri: tool.schema.string().describe("at:// URI of any post in the thread"),
    depth: tool.schema.number().describe("How many reply levels below the post").default(6),
    parentHeight: tool.schema.number().describe("How many ancestors above the post").default(10),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/thread_posts.py`
    // Guard the numeric args — the model sometimes omits them and a schema
    // default doesn't always reach here, which would send the literal
    // "undefined" (argparse exit 2).
    const depth = Number.isFinite(args.depth) ? Math.trunc(args.depth as number) : 6
    const parentHeight = Number.isFinite(args.parentHeight) ? Math.trunc(args.parentHeight as number) : 10
    return await $`python3 ${script} ${args.uri} --depth ${String(depth)} --parent-height ${String(parentHeight)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
