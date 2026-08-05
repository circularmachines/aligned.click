import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/search_posts.py — located via the git worktree so
// there are no hardcoded paths. The Python side handles Bluesky auth, the
// Cloudflare-friendly curl transport, and the stable [N] index assignment.
export default tool({
  description:
    "Search Bluesky posts. Terms are combined with AND, NOT or — a post must " +
    "contain EVERY term you pass, so a list of related topics matches almost " +
    "nothing. Search one topic at a time and call the tool again for the next " +
    'one. Use several terms only to narrow a single topic, e.g. terms: ' +
    '["mechanical design", "open source"] to find posts about both at once. ' +
    "Multi-word terms are matched as exact phrases. Returns one line per " +
    "post: `[N] @handle (K likes) " +
    "at://uri — preview`. To show a post in your reply, write just its " +
    "bracketed index like [N]; the UI renders it as a live card.",
  args: {
    terms: tool.schema
      .array(tool.schema.string())
      .describe('Search terms, each may be multi-word, e.g. ["mechanical design", "open source"]'),
    limit: tool.schema.number().describe("Max posts to return").default(10),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/search_posts.py`
    // Guard limit — the model sometimes omits it and a schema default doesn't
    // always reach here, which would send the literal "undefined" (argparse
    // exit 2).
    const limit = Number.isFinite(args.limit) ? Math.trunc(args.limit as number) : 10
    const terms = (Array.isArray(args.terms) ? args.terms : [String(args.terms ?? "")])
      .map((t) => String(t).trim())
      .filter(Boolean)
    // Each term is passed as its own argv entry (Bun escapes array elements
    // individually), so multi-word terms survive intact and Python re-quotes
    // them into exact phrases.
    return await $`python3 ${script} ${terms} --limit ${String(limit)}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
