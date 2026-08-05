import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/create_draft.py — located via the git worktree so
// there are no hardcoded paths.
//
// Like show-post, this exists for the interface rather than for data. It writes
// nothing to Bluesky and cannot: it draws a card that is edited and posted from
// the person's own session, with their own credentials.
export default tool({
  description:
    "Show a post you are proposing as an editable draft card in the chat. They " +
    "see the actual text in a box they can edit and a live count against " +
    "Bluesky's 300-grapheme limit, with a Post button that publishes it once " +
    "their account is connected. This does NOT post anything — it draws a " +
    "draft. Writing the text out in your reply instead gives them something " +
    "they cannot edit and no idea whether it fits. Call it once per draft, then " +
    "write why you are proposing it — not the text again, which is on the card " +
    "in front of them. Text only for now.",
  args: {
    text: tool.schema
      .string()
      .describe(
        "The post text, written the way they write. This is the actual post, " +
          "not a description of one.",
      ),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/create_draft.py`
    return await $`python3 ${script} --text ${args.text}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
