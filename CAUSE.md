# CAUSE — the "one AI per cause" model

Working notes on the pivot from "one AI per human" to "one AI per cause".
Captures the idea as it stands, and the design tensions to resolve before
building. Not instructions to the agent.

## The pivot

- Current product: an agent reads Bluesky *with one person*, proposes posts,
  and that person is the entire human-in-the-loop.
- Proposed: a **cause** is the unit. Many people can join a cause. Anyone can
  create a new one. A cause surfaces content; only a member endorses.
- Simpler than the chat: no conversation interface, an approval feed of
  surfaced posts. LLMs run in the background to do the surfacing.
- Working title / domain thesis: an **"ethical click farm"** — the farm is the
  suggestion, the ethics is the gate.

## What makes it ethical (the parts that cannot move)

- **Human in the loop stays.** The agent proposes; a member presses. There is
  no path to post without a person. The Post button remains the member's own
  account and their own decision.
- **Transparency label.** Every surfaced post carries provenance: why this
  cause surfaced it, which notes/terms matched, who edited them, and (per
  workstream 7) how much energy the surfacing cost. In a multi-person cause
  the label is *how* anyone trusts it, because there is no single trusted
  human behind it. The label becomes the product.
- **The re-anchoring.** "Human in the loop" moves from *one person is in the
  loop of their own feed* to *each member is in the loop of their own
  endorsement*. A cause *surfaces*; only a member *endorses*. Keep those two
  objects distinct.

## Why it is more than a feed: the cause surfaces actions too

The distinctiveness is not just *content* — a cause also **highlights the
actions its members take**. It becomes a **coordination tool around a cause**,
not a feed. Surfaced posts are the *input*; what members then did is the
*output*, and the cause brings both together.

- A member posts a reply, repost, likes a surfaced post, makes a draft, or
  takes an action in the world the cause tracks. That is an **action**, and it
  is as much the cause's content as the surfaced post was.
- The cause shows "here is what surfaced, and here is what the people in this
  cause did about it." Members can see each other's moves, which is what makes
  it coordination rather than consumption.

### What this changes

- **The transparency label extends to actions.** A surfaced post carries why it
  was surfaced; a member's action carries who did it and what it was. Provenance
  now runs on both sides of the cause, not just the input side.
- **The like/endorsement signal becomes observable coordination.** When a
  member endorses, it is not a silent vote — it is an act others in the cause
  can see and build on. The metric that scores a note is also the record of the
  cause's momentum.
- **A cause's output is as queryable as its input.** The corpus that feeds the
  classifier can also hold the actions, so the cause remembers what its members
  did, not just what it showed them.

### The tension to hold

- **Show actions, do not automate them.** The human-in-the-loop rule applies to
  actions too: a cause surfaces a member's action for others to see and build
  on, but nobody acts for a member. Surfacing an action is not performing it.
- **Attribution is the whole point and the whole risk.** Seeing who did what is
  what makes coordination possible; it is also the surface that could turn into
  performance or pressure ("look who isn't pulling their weight"). Worth
  deciding what is public, what is member-only, and whether the cause can
  celebrate a member or only show them.

## A cause is a small self-contained object

- **Keywords / search terms** — used to *search for candidates* (recall).
- **Prompt notes** — used to *classify* candidates (precision / judgment).
- **Provenance** — who edited what, when.
- Stored on **atproto**, as a readable record type, so the reader/render
  pipeline treats a cause as a first-class object and people collaborate on
  the prompt.

### Two stages, not "keywords vs content"

Retrieval (keywords/embeddings) sets the *ceiling on what the classifier can
ever see*; notes set *what of it is worth a member's time*. They are not
"early hack vs the real thing" — they are recall and precision, two different
jobs with two different edit frictions:

- keywords: broad, cheap, riffable by anyone;
- notes: the judgment, gated and versioned.

End state: text embeddings as the retrieval layer (fixes exact-phrase misses
like "repair cafe" vs "fix-it night"), keywords seeding a growing embedding
index, and the filter learning from the accumulated corpus. But embedding
does not retire the notes — it only widens recall.

## The hard part: collaborative prompt editing

Natural-language prompts are *not* mergeable like code. Two members editing
the same sentence can't be diffed, so a vote can't resolve prose the way it
resolves code. And a running classifier surfaces from its current notes.

Required structure:

- **proposal / ballot** state — a suggested note, voted on, *never* fed to the
  running agent;
- **pinned live** state — the version that actually runs, only updated from an
  accepted proposal.

Without this, either the live classifier wobbles on every edit, or the vote is
meaningless because edits hit live.

- **Governance.** "Anyone can create a cause" + "anyone edits the prompt" is a
  real request-for-power to the LLM: whoever controls the notes controls the
  surface N members see. So a cause needs an owner/maintainer role, edits are
  visible and attributed, and collaboration is propose-and-accept, not
  anyone-overwrites.
- **Vote ≠ verdict.** A vote on prose picks a winner but proves nothing about
  whether the note is *right* until members see what it surfaced. Democracy on
  a classifier requires measurement (the eval harness, workstream 3) — else
  you're voting on vibes over something that decides what people see.

## Feedback metric: likes, scored the right way

- **Likes rate the post, not the note that surfaced it.** A member likes good
  content, not "thank you keyword X." A like can't attribute credit to the
  specific note. So raw likes are a noisy signal.
- **Score the surfaced-post decision instead.** "This note proposed this post;
  did the member endorse?" That's the existing Post button turned into a
  signal — endorsed vs shown. A note that surfaces a lot but is rarely endorsed
  is a recall-bias problem; one that rarely fires but always gets endorsed is a
  precision win. Cheaper and more direct than likes, and reuses the gate.
- **Lag.** Endorsements arrive on surfaced posts, which arrive only after notes
  went live. The metric is a *steering* signal over time, not an early verdict
  on a fresh note (low-n, high-noise).
- **Taste divergence vs broken filter.** A divergence in taste is not a
  divergence in truth, and likes don't tell which kind it is. "Start your own
  cause" is the right answer to a genuinely different *view* and the wrong
  answer to a *broken filter* that the member wants fixed in place. The
  democracy must be able to say "you're wrong" (replace the note) as well as
  "you're different" (fork the cause) — else the metric rewards leaving over
  fixing, and the quality loop loses its negative feedback.

## Security notes (carried over from PLAN)

- **The corruption surface multiplies by member count.** A cause reads a wider
  stream of stranger content and hands proposals to many members. One poisoned
  post that steers a cause reaches N accounts instead of 1. The workstream-9
  isolation (agent as its own unix user, `private/` unreadable) goes from
  important to load-bearing.
- **Prompt-edit is the largest surface of all.** A collaboratively editable
  classifier can be steered *deliberately and persistently* via the notes, not
  just transiently via a poisoned post. Hence pinned-live vs proposal-ballot.

## What exists nearby (checked 2026-08-12)

- **Graze.social** — closest to the idea, and the demand proof on atproto.
  Custom feeds for Bluesky, visual node editor, AI moderation / topic /
  sentiment / text-similarity nodes, feed monetisation, stats. But feeds are
  curated by one operator, and feedback is subscriber stats — no
  collaboration, no member-likes steering the filter, no forking on
  divergence.
- **PromptTide / ThePromptSpace / Flompt / Crowd Molting** — collaborative
  prompt editing/refinement/lineage, but not tied to a live feed.
- **omens / AiFilter / Garden** — AI-filtered personal feeds (score posts,
  filter threshold, thumbs up/down), but single-user, no collaboration.

**The open spot:** collaborative, vote-governed, like-scored feed whose
prompt/notes are edited together on atproto and which forks a new cause on
divergence. That combination is unbuilt and is exactly the ethical-click-farm
thesis.

## Open questions before building

- When we say "democratic," do members who *receive* the feed vote on notes
  (collective curation), or maintainers only?
- What gets a cause onto the site, and what a cause may claim about *why* it
  surfaced a post (can it be wrong? is the label forced?).
- Does "surface good content" mean *discover and propose engagement* (current
  product, batched) or *automate the engagement itself*? Different products.
- Keywords at the start, embeddings learned from the corpus over time — is
  that the migration path, or is embeddings the target from day one?