import { tool } from "@opencode-ai/plugin"
import { $ } from "bun"

// Thin wrapper around tools/show_post.py — located via the git worktree so
// there are no hardcoded paths.
//
// The one tool here that exists for the *interface* rather than for data: it
// fetches nothing and calls no API. It's how the model asks the UI to draw
// something, through the channel it is most reliable in.
//
// Takes ONE ref, not a list. Given a list the model shows every post at once
// and writes about them all underneath, so each note ends up nowhere near its
// post. A single argument makes card-then-comment the only shape available.
export default tool({
  description:
    "Show one Bluesky post as a live card in the chat. Pass the `[N]` index " +
    "you were given by search-posts, author-posts, thread-posts or liked-posts " +
    "— e.g. ref: 3. The card appears where you made the call and whatever you " +
    "write next appears under it. Showing several posts means calling this " +
    "several times, each call followed by your comment on that one post. " +
    "Use `mode` to say what the post is being shown for: 'reply' or 'repost' " +
    "turn the card into something the creator can act on, with your proposed " +
    "words already in the box. " +
    "This is the only way to show a post. Two things never go in your reply: " +
    "the index (the reader has never seen it) and anything already on the card " +
    "— the author, the date, the counts, the post's own text and any reply you " +
    "passed in `text` are all right there, so write only what you have to add.",
  args: {
    ref: tool.schema.number().describe("The index of the post to show, e.g. 3"),
    mode: tool.schema
      .enum(["default", "reply", "repost"])
      .describe(
        "What the card is for. 'default': the post with reply, repost and like " +
          "buttons. 'reply': the post with a reply box the creator edits and " +
          "sends — put the reply you propose in `text`. 'repost': the post with " +
          "a repost box, which reposts plainly if left empty and quotes the post " +
          "if written in — put the comment you propose in `text`. " +
          "Use reply or repost whenever you are " +
          "suggesting the creator engage; a suggestion written in prose is one " +
          "they cannot act on.",
      )
      .optional(),
    text: tool.schema
      .string()
      .describe(
        "The reply or quote comment you are proposing, in the creator's own " +
          "language and voice. It is the actual message, not a description of " +
          "one, and it is theirs to edit before sending. Only used with mode " +
          "'reply' or 'repost'.",
      )
      .optional(),
  },
  async execute(args, context) {
    const script = `${context.worktree}/tools/show_post.py`
    // The model sometimes sends "3" or "[3]" rather than 3, and argparse's int
    // type would exit 2 on either. Coerce here so a stray bracket costs
    // nothing. An array slips through occasionally too — take the first.
    const raw = Array.isArray(args.ref) ? args.ref[0] : args.ref
    const ref = parseInt(String(raw).replace(/[^\d-]/g, ""), 10)
    if (!Number.isFinite(ref)) return "No post index given — pass ref like 3."
    // An unknown mode is a typo, not a reason to fail the call: the card is
    // still worth drawing, and default is the mode that shows everything.
    const known = ["default", "reply", "repost"]
    const mode = known.includes(String(args.mode)) ? String(args.mode) : "default"
    const text = args.text ? ["--text", String(args.text)] : []
    return await $`python3 ${script} ${String(ref)} --mode ${mode} ${text}`.env({ ...process.env, ACTING_SESSION: context.sessionID }).text()
  },
})
