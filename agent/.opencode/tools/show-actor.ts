import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/show_actor.py — located via the git worktree so
// there are no hardcoded paths.
//
// Like show-post and show-draft, this exists for the interface rather than for
// data. It reads one profile to check the account is real and to get its DID;
// everything else it does is ask the UI to draw a card.
export default tool({
  description:
    "Show one Bluesky account as a card in the chat — avatar, name, handle, " +
    "bio and follower counts, plus a Follow button. Pass the handle or DID, " +
    "e.g. actor: 'alice.bsky.social'. The card appears where you made the call " +
    "and whatever you write next appears under it. Showing several accounts " +
    "means calling this several times, each call followed by your reason for " +
    "that one person. This is the only way to show an account. Never repeat " +
    "what is on the card — the name, handle, bio and counts are all there, so " +
    "write only why this person is worth the creator's attention.",
  args: {
    actor: tool.schema
      .string()
      .describe("Handle or DID of the account to show, e.g. alice.bsky.social"),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/show_actor.py`
    // A leading @ is how every tool prints handles, so the model passes one
    // back often enough that stripping it here is cheaper than an error.
    const actor = String(args.actor ?? "").trim().replace(/^@/, "")
    if (!actor) return "No account given — pass actor like alice.bsky.social."
    return await $`python3 ${script} ${actor}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
