# PLAN — making the agent reliable on complex tasks

Planning doc for the humans. Not read by the agent as instructions. This
captures *what we're doing and why* before we write anything the agent
consumes (the steering doc) or any tests.

## Goal

Make this opencode setup reliably complete **complex, multi-step tasks** —
while driven by a **small local LLM**. The browser UI, streaming, and the
post tools already work. The gap is the agent's *reliability* on hard tasks.

## The constraint that drives everything

The agent will run on a **second-hand gaming machine — whatever LLM fits on
that GPU**. So assume:

- Weak reasoning, weak instruction-following, small context window.
- It will not "figure things out." It follows explicit, mechanical steps.
- Design for the *weakest* plausible model. If it works there, it works
  everywhere.

Implication: we cannot make the agent smart. We compensate with **structure**
(a fixed way of working), **robust tools** (push correctness into
deterministic code so the model does less reasoning), and **evaluation** (so
we can tell whether a change helped or hurt).

## What the fuzz-pedal session taught us

A multi-step task ("search 10 fuzz-pedal posts, get another post from each
author, make a script") exposed the failure modes that matter — independent
of that specific task, these are exactly what a weak model does by default:

1. **Trusts tool output without checking it against the request.** 3 of 9
   "author posts" were actually reposts *by different people*; the correct
   identity (the DID) was in the search output and got discarded in favor of
   the mutable handle.
2. **Confabulates instead of investigating.** It claimed an author "changed
   their handle" — false — to explain a surprise rather than checking.
3. **Never verifies the result against the task.** Nothing checked "another"
   (distinct) or "each author" (same identity).
4. **Loses / under-reports results.** "Show them" surfaced one wrong item
   instead of the collected set.

These are process failures, not knowledge gaps. That's the good news: they're
fixable with structure and tooling, not a bigger model.

## Projects — the unit the agent works in

The agent should always run **inside a project**: a folder (today `agent/`)
that is its workspace. The boundary rules:

- **Reads:** may read the repo root (shared context) freely.
- **Writes:** may write **only inside its own project folder** — never the
  repo root or another project.
- **Cross-project reads:** decided *per project* (a project opts in to reading
  specific others). Default: only its own folder + repo root.
- **Private vs public projects — via two agents (VERIFIED).** Rather than
  per-project rulesets, define two agents: a **public agent** whose read
  permission denies the private area, and a **private agent** that can read
  it. All private projects live in one `.gitignored` `private/` folder.
  Confirmed working against 1.16.2: a `publictest` agent with
  `read: { "*": "allow", "*private*": "deny" }` refused to read
  `private/secret.txt` ("access … is denied") while the default agent read it
  fine — and it did *not* hang (no `ask`). This is the mechanism the two-agent
  model rides on.
- **Shared infrastructure lives outside projects (DONE).** Reorganized so
  shared bits sit at the repo root and the agent's own directory holds only
  what configures it. `agent_area/` was that directory until 2026-08-05, when
  it turned out to be an empty folder opencode had to walk up out of to find
  its configuration; `agent/` holds the configuration and is the workspace.
  - `tools/*.py` — the Bluesky scripts (moved out of the agent's folder).
  - `AGENTS.md`, `OPERATING.md` — domain + operating instructions, loaded for
    every project (AGENTS.md via the cwd→root walk; OPERATING.md via
    `instructions` in `opencode.json`).
- **The post tools are now proper opencode tools (DONE).** Instead of the
  agent shelling out to `python3 <path>` (which needs a hardcoded path — bad
  for shareable code), each tool is a tiny TS definition in `.opencode/tools/`
  (`search-posts.ts`, `author-posts.ts`) that runs the Python script located
  via `context.worktree` — no hardcoded paths, registered as named tools the
  model calls directly. opencode's rule: the tool *definition* must be TS/JS,
  but it may invoke a script in any language. Verified end-to-end.
- **Public/private agents (SUPERSEDED 2026-08-05).** `opencode.json` defined a
  `public` agent (`read`/`edit` deny on `*private*`) and a `private` agent
  (full access), and the fence itself was confirmed: public was denied
  `private/secret.txt` with a real permission error while private read it.
  What the test could not show is the hole beside it — **a session that names
  no agent gets opencode's default**, which neither block touched, so for
  weeks the rule was real and reached nothing (see §9). The agents now are
  `build` (the default, and where the denials live), `focused` and `builder`;
  a person's line in `users.json` decides which they may name.

### How opencode supports this (researched from source)

opencode has first-class primitives for all of this, so we lean on them
rather than build our own:

- **Agents.** A named agent is a markdown file `.opencode/agents/<name>.md`
  (YAML frontmatter + body-as-system-prompt) *or* an entry under the
  **`agent`** key (singular) in `opencode.json`. Fields: `description`
  (required), `model`, `prompt` (system-prompt file), `mode`
  (primary/subagent/all), `temperature`, `steps`, `permission`. The UI selects
  it via the `agent` field in `prompt_async`. → **We formalize our setup as
  defined agents** (public + private): model = gemma, prompt = operating
  instructions, `permission` = the project boundary below.
- **Permission format (opencode fails SILENTLY if this is wrong).** The
  `permission` key (singular) is an **object keyed by tool** —
  `read`, `edit` (write/edit/apply_patch), `bash`, `external_directory`,
  `glob`, `grep`, `list`, `webfetch`, … — each value either `"allow" | "ask"
  | "deny"` or a `{ "glob": action }` map (last matching glob wins). NOT an
  array of `{action, resource, effect}` (that is the internal representation;
  using it makes opencode quietly refuse to create sessions). Docs:
  opencode.ai/docs/agents, opencode.ai/docs/config.
- **The filesystem boundary is built in.** File tools resolve paths against
  the session's **directory** (its cwd). Anything outside it is "external"
  and triggers an extra `external_directory` permission check; relative paths
  that escape the directory are hard-errored. → **Run each session with
  `directory` = the project folder**, and writes outside it are already gated.

### Constraints / open design points for projects

- **No `ask` in our headless UI.** We have no permission-prompt endpoint, so
  any rule resolving to `ask` would hang (same failure class as the disabled
  `question` tool). Every action must resolve to `allow` or `deny`. So the
  agent's ruleset must *explicitly* allow reads/bash/in-project-writes and
  deny out-of-project writes — never leave it at the `ask` default.
- **Read-root-but-write-only-project needs care.** External reads and external
  writes share the same `external_directory` gate, so we can't just deny that
  gate (it would also block reading the repo root). The write restriction has
  to key on the resource path (external/absolute paths → deny `edit`/`bash`)
  while keeping reads allowed. Exact ruleset is an implementation detail to
  nail down and test.
- **Per-project rules.** Because the write-allow path is project-specific,
  either one agent definition per project, or one agent whose `directory` is
  the current project + a project-agnostic ruleset (deny external writes,
  allow internal). Leaning on the latter (the built-in directory boundary).

## Root = infrastructure, project = specialization (refinement 2026-07-23)

Backing off the "everything at root, shared by all projects" shape. New
direction: **the root repo is plain infrastructure; the domain "special
functions" live in each project.** Opening a *new* project should start the
agent as a **general code + process agent** (a builder), and the project's
special functions accrue on top of that over time and specialize it. Bluesky
stops being the repo's identity and becomes just *one project*.

### What opencode allows (researched, decisive)

- **Instructions are per-folder.** opencode walks *up* from the session's
  `directory` loading `AGENTS.md`, so a project folder can have its own
  `AGENTS.md` that only applies there; `instructions` also takes globs like
  `packages/*/AGENTS.md`. → per-project **domain instructions** work.
- **Custom tools are NOT per-folder.** `.opencode/tools/` is discovered only
  at the **git worktree root** or **globally** (`~/.config/opencode/tools/`),
  and tools are compiled once at server startup. → a project *subfolder*
  cannot carry its own tools.

### Implied shape

Because the domain "special functions" include **tools** (the Bluesky ones
are), projects can't be plain subfolders of the infra repo:

- **A project is its own opencode root** (own repo/worktree) with its own
  `.opencode/tools/`, `AGENTS.md`, and memory/DB. "Opening a project" =
  pointing/launching opencode at that folder so its tools get discovered and
  compiled (likely a serve instance rooted in the project — tools load at
  startup, not per session `directory`).
- **Infra stays generic**: the browser UI + a launcher, plus the *generic*
  capabilities — the operating loop and `delegate` / `append-note` /
  `search-notes` — provided **globally** (`~/.config/opencode/tools/` + global
  `AGENTS.md`) so every project inherits them without copying.
- **Bluesky becomes one project**: its post tools, its `AGENTS.md`, and its
  corpus DB move out of root into that project.
- **New project = a code + process scaffold**: generic builder agent, generics
  inherited, no domain tools yet.

### First consumer: the strategizer (2026-07-26)

The engagement strategizer (`STRATEGIST.md`) is the first thing that actually
tests this refinement, and it splits the idea into **three** layers rather than
two:

- **Infra** — this repo: opencode, the chat page, streaming, the `[N]`
  post-card contract, `OPERATING.md`, `delegate` / notes.
- **Capability** — the Bluesky tools and the creator pipeline. Tools stay at the
  worktree root, because a tool is a capability, not a product decision.
- **Product** — what a re-publishing plan *is*, its formula prompt, its output
  format. Lives in `products/<name>/`, and a product is really just a URL, an
  agent, and a versioned prompt template.

**The rule this repo has to hold: `AGENTS.md` and `OPERATING.md` never mention
re-publishing plans, creators-as-customers, or any other product concept.**
They describe what the tools are and how to work; the product describes what to
produce. A useful consequence: *workflow* discipline is product knowledge —
`OPERATING.md` stays generic, while a product's ordered steps live in its own
prompt, because a second product would keep the former and replace the latter.

No repo split yet. `.opencode/tools/` loads only at the worktree root, so a
product in a subfolder can't carry its own tools; the conceptual separation is
worth having now, the migration only when a second product or a deployment
forces it.

### Open points

- **Generic tools: global vs. scaffolded.** Provide `delegate`/notes/etc.
  globally in `~/.config/opencode/tools/` (one copy, every project inherits —
  *leaning this*) vs. copy them into each new project (self-contained but
  duplicated).
- **One serve per project vs. one serve, many dirs.** Since tools compile at
  startup from the worktree root, per-project tools probably need a serve (or
  `opencode run --attach`?) rooted in the project. Confirm whether a single
  serve can host sessions in different project roots with different tools, or
  whether "open project" means (re)starting/attaching a serve there.
- **Migration.** Move `tools/*.py`, `.opencode/tools/*.ts` (Bluesky), and the
  domain `AGENTS.md` out of root into a `bluesky` project; promote the generic
  tools + operating loop to the infra/global layer. `OPERATING.md` is generic
  (infra); `AGENTS.md` is domain (project).

## Persistence & memory (next up — direction agreed, details open)

Discussion 2026-07-23. The current setup conflates several kinds of state. We
separate them into **three distinct layers**, each with its own lifetime,
storage, and tools:

1. **Corpus — facts about the world (the posts themselves).**
   - `.post_index.jsonl` is a degenerate version of this: it stores only
     `index → URI`, and `assign_indices` linearly rescans the whole file on
     every call. It will **not scale**.
   - **Decision: move to SQLite** (`sqlite3` ships with Python; one gitignored
     file; scales to millions of rows; has **FTS5** full-text search). One
     `posts` table where the `[N]` index is just the autoincrement rowid, plus
     the full post: `uri` (unique), **`did`**, `handle`, `text`, `like_count`,
     `created_at`, `seen_at`.
   - Payoffs beyond scaling: (a) storing the real **`did`** kills the
     repost/identity bug (see the fuzz-pedal section — stop trusting the
     mutable handle); (b) an FTS index over `text` is the mechanism for
     "**expert in what posts exist**" — the agent searches its own
     accumulated corpus offline and cites posts known to be real instead of
     guessing; (c) grows **passively** — every `search`/`author`/`thread`
     call writes what it fetched, no new agent behaviour needed.
   - UI unaffected: tools still print the same `[N] … at://` lines that
     `scanForPostIndices` reads.
   - Migration: seed the table from the existing `.post_index.jsonl` so old
     `[N]` references stay stable (low stakes — it's gitignored dev state).
   - Endgame for real breadth: active crawling via the atproto **Jetstream
     firehose** into the corpus. Later phase, heavier.

2. **Project memory — intent + lessons ("keep the agent on point").**
   The thing that makes the agent "learn what the user is looking for and not
   repeat old mistakes." Per-project and small, so keep it **human-readable**:
   a `PROJECT.md` the agent reads at task start (step 0, next to
   `search-notes`) and updates through a `remember` tool with **typed entries**
   — *goal / preference / lesson* — using the same append-safe pattern as
   `append-note`. Legible so the user can read and correct it. (Mirrors the
   assistant's own file-based memory model.)

3. **Working notes — this request.** `NOTES.md`, already built. Transient
   findings for the current multi-task job; the durable stuff gets *promoted*
   into project memory (layer 2).

### Layout sketch (pending the "corpus scope" decision below)

```
at_opencode/
  posts.db          ← shared corpus: did, text, FTS (gitignored)   [if shared]
  agent_area/       ← a project
    PROJECT.md      ← intent + lessons (curated, human-readable)
    NOTES.md        ← this-request findings (transient)
  private/projX/    ← a private project, same shape
```

### Open decisions (deferred — decide before building)

- **Corpus scope.** Shared repo-root `posts.db` (knowledge compounds across
  projects — best for the "expert" goal; posts are public so no privacy issue)
  vs. per-project db (isolated but no broad expertise, re-fetches everywhere)
  vs. shared corpus + per-project `[N]` index (more moving parts). *Leaning
  shared.*
- **Project-memory storage.** `PROJECT.md` + `remember` tool (human-readable,
  weak-model-friendly structured appends — *leaning this*) vs. a SQLite
  `memory` table (queryable, not legible) vs. a free-form file the agent edits
  wholesale (weak model mangles free-form edits — least reliable).
- **Sequencing / what to build first.** (a) SQLite corpus (foundational,
  low-risk, unlocks scaling + FTS expertise), (b) a **minimal eval harness**
  (5 checkable tasks + runner — turns "I suspect gemma misuses the tools" into
  measurement *before* we build more), or (c) project memory (`remember` +
  step-0 wiring). See the caveat below.

### The measurement caveat (why this matters now)

We're ~6 tools deep (search/author/thread/delegate/append-note/search-notes)
with **zero measurement** of whether the weak model calls them at the right
moments. "The tools need to be used correctly" is currently unfalsifiable. A
tiny eval harness (Workstream 3, overdue) is the only way to tune the tool
descriptions and `OPERATING.md` so gemma actually *uses* this architecture
instead of ignoring it. Build a minimal version **alongside** the projects
work, not after.

## Workstreams

### 1. Agent operating structure (the future steering doc)
A fixed "way of working" the agent follows on every task: restate the task as
checkable requirements → plan → do one step → verify the output against
intent → check the finished result against the requirements → report
honestly. **Not written yet** — depends on decisions below. Kept separate
from `AGENTS.md` (which stays *what exists*: tools, conventions, domain).

### 2. Tool hardening
Make the tools hard to misuse so the weak model can't easily go wrong. The
repost/identity bug is half a *tool* problem: tools should surface stable
identifiers (DIDs), flag reposts, and fail loudly rather than returning
plausible-but-wrong data. Principle: **move correctness into deterministic
tools**, leaving the model as little judgment as possible.

### 3. Evaluation suite (~20 tricky tasks)
The regression guard the user asked for: a set of tasks with **checkable
success criteria** and a runner that scores the agent, so improvements don't
silently wreck old functionality. Build a minimal version *early* so we're
not flying blind while changing the other two workstreams.

#### Route the binary decisions to their own agent (agreed 2026-07-28)

The suite has been stuck on "what is a success criterion for a plan?", which is
the wrong question to start from. Some of what the agent does is not a plan at
all — it is a **decision with an answer**, and those can be scored without
judgment, without a rubric and without a judge model. Pull them out and they
become measurable; leave them inside a conversation and they never will be.

**One decision, one agent.** opencode already gives us agents with their own
prompt, model and tool set (`public`, `strategist`, `worker`). A `matcher` agent
that only ever answers "is this Bluesky account this person, yes or no, and on
what evidence" is:

- **evaluable in isolation** — the same input can be replayed a thousand times
  with no conversation around it,
- **swappable** — a decision that turns out to need a stronger model can have
  one without paying for it everywhere else, and equally a weaker one,
- **unbudgeable** — it cannot be talked out of its output shape by three
  paragraphs of chat that happen to precede it, which is a real failure mode
  with a weak model.

**A decision is only evaluable if its input can be pinned**, and that is what
picks the candidates for this treatment. Person matching qualifies: the input is
a stored `subjects` row plus a candidate actor profile, both of which are just
records we can snapshot. "Write a re-publishing plan" does not: its input is
everything the agent has read.

**That answers open question 3 for this class of task.** Snapshot the candidate
profiles into the fixtures rather than calling `searchActors` live. Otherwise the
score moves when Bluesky moves and a regression is indistinguishable from
somebody editing their bio. The retrieval step — did we surface the right
candidate at all — is a separate measurement with its own, necessarily live,
answer.

**And it makes scoring boring, which is the goal** (open question 4). A binary
decision against a label needs a comparison, not a judge model. The runner is a
loop, a dict of labels and a confusion matrix. Everything expensive and arguable
about evaluation lives in the tasks we *cannot* reduce to this — so the more we
can, the smaller that problem gets.

What each measurable thing means for the product, including why "95%" needs
saying more carefully than it sounds, is in `STRATEGIST.md`.

### 4. Project & agent structure
Formalize the agent as a **defined opencode agent** scoped to a **project
folder**, with the read/write boundary above enforced via permissions. Move
shared tools out of `agent_area/`. This is the container the other three
workstreams live inside — the operating structure becomes the agent's system
prompt, tool hardening applies to the shared tools, and eval tasks run against
a defined agent in a defined project.

### 5. Output checks + a correction loop (TODO, added 2026-07-26)
Right now nothing inspects what the model *produced*. Every guard we have is on
the input side (tool descriptions, operating steps) or inside the tools. But
some failures are only visible in the finished answer, and they're mechanically
detectable:

- **A `[N]` post index inside a markdown table.** The UI replaces it with a
  full-width card, which a table cell can't hold, so the layout breaks. Seen in
  `ses_06231e268ffegDJX4Kwbai40lr`.
- **A `[N]` that no tool in this session returned** — the confabulation check.
  Cheap: collect every index the tools printed, diff against the indices in the
  reply.
- **A raw `at://` URI written out**, which `AGENTS.md` forbids.
- **A claimed count that contradicts the tool output** (see the truncation bug
  in that same session).

The check is easy; the interesting design question is what to do on failure.
Options: reject and re-prompt the model with the specific violation (a loop —
costs a turn, and a weak model may not fix it); repair deterministically in the
UI (silent, always works, but hides the problem); or surface it to the user as
a warning on the message. Probably different answers per check — repair the
table, loop on a fabricated index.

Ties into Workstream 3: each check is also a scorable assertion, so building
them gives the eval harness its first real metrics for free.

### 6. Rendering belongs to tools, not prose (built for posts, 2026-07-27)

Today the UI scrapes the assistant's *reply text* for `[N]` and swaps in post
cards. That has cost three separate rules in `AGENTS.md` — write the bracketed
index, never write the raw `at://` URI, never put an index in a table — and
every one of them was added after a real failure. It asks the weakest component
in the system for prose-formatting discipline, which is the thing it is worst
at.

**Invert it: the model calls a tool, and the UI renders the tool's output.**
Models are trained hardest on tool calls; that is the most reliable channel we
have. A `show-post` tool takes the posts to display and the UI turns its output
into cards. Every formatting rule above then disappears, because there is no
prose to get wrong.

Points that fall out:

- **`[N]` survives as the tool's *input*.** Passing `refs: [3, 7]` is far easier
  for a weak model than reproducing a URI, and the index already exists.
- **The mechanism is already there.** The UI watches tool output today —
  `scanForPostIndices` reads it to build the index map.
- **Placement now works.** A card renders where the call happened, and since the
  turn renders chronologically, that is the right place: call, card, commentary.
  This was not true when tool output was pinned above the answer.
- **It removes the reason for part of Workstream 5.** The `[N]`-in-a-table check
  exists only because refs live in prose; no prose refs, no check.
- **Same shape covers drafts** — a `draft-post` tool rendering an editable card,
  which is where the product needs this to go anyway (see `STRATEGIST.md`).

Worth doing even though the current scraping "works": it works at the cost of
three rules a weak model has to remember on every reply, and it has already
failed twice in observed runs.

#### What shipped, and what the first run taught

`show-post` (`tools/show_post.py`) takes **one** index and emits a payload the
UI renders as a card. The channel is one line at the end of a tool's output —
`RENDER {json}` — dispatched on a `kind` field, so the next render tool needs a
renderer in the UI and nothing else. See `tools/render.py`.

It works: the model calls it, the card appears where the call happened, and the
post renders in full — avatar, handle, date, text, images, counts. Four things
the working version turned up that the plan above did not predict:

- **The index leaked into the reply, and that was the real defect.** The model
  called the tool correctly and then still wrote "`[2408]` — a beautiful digital
  painting". `[2408]` is machinery: the reader has never seen it, there is no
  number on the card to match it against, and it cannot be looked up. The rule
  that replaced the three old ones is therefore not *how* to write a reference
  but **not to write one at all**. Told that, the model wrote `#2443` instead —
  it wants to label what it just showed, and banning one spelling only moves it
  to the next, so the UI now strips any index-shaped token that resolves to a
  post it drew. Substituted with "This post" rather than deleted, because the
  model uses it as the subject of the sentence and cutting it leaves a fragment.
- **A card must be created once and never re-parented.** `<atproto-post>` aborts
  its fetch on disconnect and does not restart on reconnect, and `drawPending`
  was calling `replaceChildren` on every animation frame — so every card sat in
  its loading skeleton forever. The old prose path never hit this because it only
  ran on the final render. Anything rendered *during* a turn has this property,
  so the bubble is now patched in place. This will apply to draft cards too, and
  more sharply: an editable card that gets re-parented loses what was typed into
  it.
- **The model batches when told not to, so the tool takes one post.** "One call
  per post, then your comment" was in the tool description *and* the
  instructions; it passed `refs: [3, 7]` anyway and got two stacked cards with
  both notes underneath. The argument is now a single `ref` — named `show-post`,
  singular — and the shape is structural rather than requested. One tool call per
  post is the right price for that.
- **A card makes most of the commentary redundant, and the model writes it
  anyway.** Its first pass read "@sandboxalchemy.bsky.social (July 17) — digital
  painting, 26 likes and 7 reposts", every word of which was already on the card
  in the real thing's own formatting. Showing the post changes what there is to
  say about it: the note is what you are *adding*, and nothing that is on screen
  already. The same trap is bigger for `draft-post` — the draft text is in the
  card, so describing the draft is pure repetition.
- **A failed tool call showed as still running, forever.** `show-post` rejected a
  bad argument in 33ms and the trace kept its `…` marker for the rest of the
  session, so the turn looked stuck on it. Error status now renders as `✗` with
  the error text. Unrelated to this workstream; it only became visible because a
  schema change made the model fail a call.

**The remaining gap is narration, not rendering.** With a weak model
(`minimax-m2.5`) the mechanism is reliable — right post, right place, every time
— but it saves its commentary for the end of the turn instead of writing it
after each call, so the notes end up in a block below both cards. Every observed
run did this.

Two attempts at fixing it by instruction have failed. The second is the
interesting one: the ask was moved *into the tool's own output* ("write what you
have to add now, before showing another post"), on the theory that a rule
arriving at the moment of decision beats one sitting thousands of tokens back in
AGENTS.md. That theory is probably right in general and the injection is worth
keeping — it costs nothing and it is the correct place for a just-in-time rule —
but it did not move this model.

The likely reason is structural rather than a matter of persuasion: in every run
the model emits its whole tool sequence and only then produces a text part, which
is what a model trained to answer *after* acting does. If it cannot emit text
between two tool calls in one turn, no wording will fix it. Two ways out, neither
tried: have `show-post` take the note as an *argument* so the card and its
comment arrive in the same call and the UI renders them together — the same
inversion as the workstream itself, applied one level further — or structure the
product plan so each post is its own turn. The first is cheaper and worth trying
before blaming the model.

**Second renderer: `show-draft`.** An editable proposed post — text, pictures,
alt text, live grapheme count, Post button. It cost one new `kind` in the
payload and one function in the UI, which is the evidence that the `RENDER`
channel was the right shape. Details in `STRATEGIST.md`; the tool itself knows
nothing about re-publishing plans, because it is infrastructure and that is the
product's word.

**Third renderer: `show-actor` (built 2026-07-28).** Same inversion, applied to
people. Job B of the strategizer is entirely about *people* — which of your
contacts is here, and which of them is worth reconnecting with — and describing a
person in prose has exactly the defect describing a post had: the reader can see
the handle, the bio and the follower count perfectly well, so the agent spends
its sentences restating what is on screen instead of saying why this person.

An actor card is also the only place the product's one real action can live. So
it carries a **follow button, dummy at first**:

- **A dummy is the honest first version, not a shortcut.** `v1 writes nothing to
  Bluesky` is a settled decision; the draft card's Post button went the same way,
  mock until the session had credentials. Drawing the button establishes what has
  to exist around it — where the action sits, what it says, what the card looks
  like afterwards — while the write path stays absent.
- **It has to be visibly inert.** A button that looks live and silently does
  nothing is the worst state to leave in front of a real creator: they will
  believe they followed someone. Disabled, labelled as not wired up yet.
- **Following needs auth like posting does** — per-session credentials, the
  creator's own account. The two share a path, so whichever lands first decides
  the shape for both.

It does ship one — `<atproto-profile>`, taking a handle, DID or at-uri as `src`
— so the card is the library's and the follow row underneath is ours. Three
things the build turned up:

- **The library's counts are wrong, so they are hidden.** It derives them by
  walking records rather than asking the appview, and reports 12.7M followers
  for `@bsky.app` against the real 34.3M, and "500+ posts" for an account with
  802. Whether someone is worth the creator's time is partly a question about
  their size, so `::part(stats)` is hidden and the row is redrawn from the
  `getProfile` the tool already makes to resolve the DID. Worth knowing
  generally: these elements are styleable through `part`, so a card can be
  corrected without being replaced.
- **A payload field name collided across kinds and cost a whole turn.** The
  dedupe loop read `render.posts` off every payload; on an actor payload that is
  a post *count*, and `for (const p of 5039)` threw inside the one loop that
  draws everything — so the second card and the entire reply text vanished, with
  the session showing both tool calls completed. Fixed twice over: the dedupe is
  scoped to `kind === "posts"`, and `renderElement` is wrapped so a renderer that
  throws costs its own card and falls back to the trace line. **A field means
  something only within its own `kind`** — worth remembering as the channel grows.
- **The narration gap is exactly as it is for posts.** Both cards, then both
  notes at the end, and the notes repeat the bio and the follower count that are
  on screen directly above them. Unchanged by the tool being new, which is
  further evidence it is structural rather than a wording problem.

**The card carries the intention, via a `mode` argument (2026-07-28).**
`show-post` now takes `mode` — `default`, `reply` or `repost` — and a `text`
prefill. Reply, Repost and Like sit on every card regardless; the mode only
decides which box is already open and holding the agent's words. **The agent
proposes, it does not narrow**: a creator who is shown a quote and would rather
reply is one click away, and gets an empty box, because a comment written to
head a quote post is not a reply to its author and carrying it across would put
words in their mouth nobody chose. Both boxes share the draft card's compose
box, so a proposed reply is counted against the same 300-grapheme limit as a
draft, by the same code.

This is **the deferred tool-input idea arriving from the other direction**. The
open problem above is that the model saves its commentary for the end of the
turn, and the untried remedy was to take the note as an argument so the card and
the words arrive together. That has now happened for the *action* rather than
the note: "you could reply something like…" in prose is a suggestion nobody can
act on, while the same sentence passed as `text` lands in a box the creator
edits and sends. Worth watching whether it helps the narration problem too — it
removes one of the things the model was saving up to say.

**Nothing the reader does in the UI reaches the agent.** Every button that
writes is disabled; the ones that are pressable (which box is open, the like
mark) only change what the card shows. Nothing leaves the browser: the only
path back to the session is the composer. Two consequences to settle before any
of these buttons go live:

- **An edit is invisible.** If the creator rewrites the draft and asks "is that
  under the limit?", the agent answers about the text *it* proposed, because
  that is the only version it has. The card and the conversation are two states
  of the same thing, and only one of them is in the transcript.
- **An edit does not survive a reload.** Cards are rebuilt from the tool output
  in the message history, so anything typed into one is gone.

The shape of the answer is probably that a real action posts a short user-role
message back into the session — "posted the draft as: …", "followed @x" —
because that is the one channel the agent already reads, and it makes the
transcript the record of what happened rather than of what was suggested.

Still to do: deleting the prose-scraping path once the tools have been used
enough to trust. It stays for now as a fallback, harmlessly — cards it would
duplicate are deduped against what the tool drew.

### 7. Capture what we spend in energy (TODO, investigated 2026-07-27)

GreenPT returns the environmental cost of **every** call, in the response body,
with no extra request:

```json
"impact": {
  "version": "20250922",
  "inferenceTime": { "total": 163,   "unit": "ms" },
  "energy":        { "total": 58505, "unit": "Wms" },
  "emissions":     { "total": 231,   "unit": "ugCO2e" }
}
```

Note the units — **watt-milliseconds** (÷3,600,000 for Wh) and **micrograms**
CO₂e — and the `version` on the methodology, which means the numbers can be
compared over time rather than being a vibe. Measured: a 5-token reply is
0.016 Wh / 0.23 mg; a 300-token paragraph is 0.570 Wh / 8.1 mg. **No water
figure** — the site claims their cooling uses a fraction of the usual and gives
no number, so a water number would have to come from asking them. There is no
aggregate endpoint (`/v1/usage` and `/v1/impact` are both 404), so a running
total has to be accumulated on our side.

Worth having for a reason beyond bookkeeping. The strategizer's whole argument
is *engagement you would want to receive*, made by an organisation that is a
non-profit rather than a growth product. "This plan cost 0.4 Wh to produce" is
the kind of claim that makes that credible, and it is a measurement rather than
a position. It is also the honest counterweight to running a vision model over
every image a creator has ever posted.

**Two paths, and only one of them is hard.**

*The direct calls are free to instrument.* `tools/vision.py` talks to GreenPT
itself, so it can read `impact` off the response today — two columns on the
analyses table and every image carries its own cost. This is also where the
volume is: the 169-call batch on 2026-07-26 dwarfs any number of agent turns.
Do this first; it needs no infrastructure and nothing else depends on it.

*The agent's own turns need a proxy.* Verified on 2026-07-27:

- The data **is** in the streaming response, in the final chunk beside `usage`,
  so it survives the wire format opencode actually uses.
- opencode **stores none of it**: an assistant message keeps `tokens` and `cost`
  and nothing provider-specific.
- **No plugin hook can reach it.** The hooks are `chat.message`, `chat.params`,
  `chat.headers`, `tool.execute.before`/`after` and `permission.ask` — every one
  request-side or tool-side. There is no response hook.

The cause is `@ai-sdk/openai-compatible`, which parses against a Zod schema and
drops unknown top-level fields. Keeping `impact` needs its `metadataExtractor`,
which is a *function*, and opencode's provider `options` come from JSON — so it
cannot be set from config at all.

So: point the provider's `baseURL` at a small local proxy that forwards to
GreenPT and tees `impact` off each response. What makes that a design rather
than a hack is `chat.headers`: a plugin can stamp `sessionID` and agent name
onto every outgoing request, so the proxy attributes energy **per session and
per agent** instead of as one anonymous total — which is what makes "what did
this strategist run cost" answerable.

Three things to get right:

- **Forward the incoming `Authorization` header untouched.** The proxy then
  never holds a key, and the existing arrangement (the key lives in opencode's
  config, and never reaches the browser) is unchanged.
- **Stream through without buffering.** It sits in front of every agent call, so
  if it stalls the agent stalls. It must be dumb.
- **The provider config is global** (`~/.config/opencode/opencode.jsonc`), so
  repointing `baseURL` changes every opencode session on the machine, not just
  this repo. That is the real cost of this half, and the reason to do the vision
  half first and decide on the proxy separately.

### 8. A left pane a product can fill (TODO, agreed 2026-07-27)

The chat is the whole window today. But a product needs somewhere to put things
that are **not part of a conversation** — state you set once and then work
against, and readouts that are true continuously rather than at one moment in a
transcript. Those things read badly as chat messages: a form that arrives as a
message scrolls away, and a total that updates has no business being a fixed
line in a transcript.

So: **a left pane, owned by the product, alongside the chat.** No product (plain
`/`) means no pane and the chat keeps the window.

**The general mechanism is the point.** This should not be strategist-specific
plumbing that a second product has to fork. The rule that already works for
prompts extends cleanly: the product directory owns its pane, so
`public/products/<product>/pane.html` is loaded whenever that product is active,
exactly as `prompt.md` already is. Adding a pane to an experiment is then adding
one file, and a product with no `pane.html` simply gets no pane.

What has to be decided before building:

- **The pane needs a backend, and that is the real cost.** `serve.py` currently
  serves static files and one read-only `/media/` route. Editing creator fields
  needs a write endpoint; a drop zone for export files needs an upload endpoint.
  That is a genuine step up — and it collides with a rule worth keeping:
  `sync/store.py` is *the only writer* of `private/external.db`. Best shape is
  probably that the pane writes **files** (a JSON edit, a dropped archive) and
  never the database, leaving the human-run sync as the only thing that ingests.
  **Settled in the pane's favour by building the LinkedIn importer
  (2026-07-28):** every field the pane would edit is a field of
  `private/creators.json`, including the new `exports` map whose date the
  importer derives an archive's path from. So the pane writes one JSON file and
  drops archives in a derived directory, and a human with a text editor does
  exactly the same thing — which is what keeps the pane optional rather than
  load-bearing.
- **Isolation vs. conversation.** An `<iframe>` stops a half-finished
  experiment's pane from breaking the chat, but then the two have to talk over
  `postMessage`. Injecting it inline is simpler and shares everything, including
  bugs. Lean iframe, because the whole reason for a pane per product is that
  products differ.
- **Keep the scrape allowlist out of it.** Requiring a hand edit to mark a
  creator scrapeable is deliberate — a gate before spending money on a real
  person's data. A pane that makes every field editable quietly removes that
  gate. The allow flag stays file-only, or it stops being a gate.
- **Layout.** A left pane ends the centred single column; the shell becomes two
  columns, and the pane collapses on a narrow screen rather than squeezing the
  chat.

**It gives Workstream 7 somewhere to live.** A running energy/CO₂ total is
exactly the kind of continuously-true readout that has no place in a transcript,
and the pane is where it goes — which also means the agent-side half of 7 (the
proxy) has a visible payoff rather than being bookkeeping nobody sees.

### 9. The tool surface, and a coding agent that is called rather than always present (2026-08-04)

**v1 gives the agent no built-in tools at all.** `opencode.json` denies by
wildcard and re-enables the thirteen Bluesky tools by name, so a built-in
opencode adds next month is off by default rather than on. Three things were
learned getting there, and each cost something to find.

**A large tool payload breaks some models.** DeepSeek V4 Flash, with ~23 tools
(thirteen custom plus opencode's built-ins), emitted DeepSeek's own DSML tool
syntax as assistant text instead of using the `tool_calls` field, then read back
its own malformed output and looped: fourteen turns for a one-word prompt.
Bisected to rule out the obvious: not the server (a bare `opencode serve`
worked), not GreenPT, not the provider package, not any single schema. Thirteen
tools were fine, twelve were fine, one was fine. It was the size of the payload.

**Filesystem tools make it loop even when they work.** The same search takes
four turns with the Bluesky tools alone and twenty-eight once `read` and `grep`
are there — the same answer for seven times the energy. That tracks the
*presence* of those tools rather than their number, and reads like a prompt
problem: `OPERATING.md` opens with "You are an investigator", so given grep it
investigates the filesystem instead of Bluesky.

**A denial written in the wrong place looks exactly like one that works.** The
rule making the shared workspace safe was set on the `public` agent — and a
session created without naming an agent gets opencode's *default* agent, which
that block never touched. Verified by reading, believed for weeks, and doing
nothing: the model ran `echo diagnostic` and it executed. It belongs at the top
level, where it reaches every agent.

**Next iteration: a coding agent that is called, not carried.** Reading, writing
and running scripts are worth having, and the way to have them is a separate
agent the main one invokes for a task — not a shell hanging off every
conversation. It gets a session-specific working directory, and the main agent
gets a tool that hands it a job and takes back a result.

What has to be true first, and it is not a matter of configuration:

- **`bash` cannot be confined by opencode's permissions.** The `read` rule takes
  path globs, so `*private*` can be denied — verified. The `bash` rule takes
  *command* patterns and has no idea what path a command touches, so
  `cat private/oauth/sessions.json` is not covered by it. That file holds
  refresh tokens and DPoP keys for every account that has logged in, which makes
  this the difference between one user and one user reading everybody.
- **So the boundary has to be the operating system.** Run opencode as its own
  unix user that cannot read `private/`, and a shell is confined by file
  permissions rather than by string matching.
- **One thing blocks that split today**: `tools/bsky.py` reads
  `private/proxy-sessions.json` to map a session to its owner, and that file
  also holds login cookies. The proxy should write a separate
  `session-owners.json` holding only `{session: did}`, readable by the agent's
  group, leaving `private/oauth/` at 0700.

**Where this landed (2026-08-05).** The mechanism now exists and the isolation
still does not, and it is worth being exact about which is which.

Agents carry their own `permission`, and an agent's rule is applied *after* the
config's — measured on a throwaway server rather than assumed, by reading the
resolved rule list back from `GET /agent`. So `builder` ends on `bash: allow`
while the default agent ends on `bash: deny`. That is what makes "bash for one
person and not another" expressible at all: a prompt carries a model, a tool
list and an agent, but never a permission.

The top-level `permission` block is gone, because it was the thing every
override had to fight. Each agent states its own policy instead, and the
protection is unchanged: an unnamed session runs opencode's `build` agent, which
now carries the denials the top level used to.

Two gates stand between a user and a shell — the agent must be *named* in the
prompt, and the caller's line in `users.json` must list it. Nobody has it but
Johan. That also closed a hole that was already open: `?product=<name>` put a
name straight into the prompt body, so any user could have asked for any agent.

**What is still true from the list above:** `builder` runs with the repository as
its working directory, and `private/` is in it. A prompt injection carried in a
Bluesky post that the agent reads can spend that shell, and refresh tokens for
every account that has logged in are one `cat` away. Nothing above changes that
— the unix-user split is still the fix, and until it lands, `builder` is a tool
to use on a conversation you started and not on one that has been reading
strangers.

## Next up (shortlist, 2026-07-28)

Four things, three of which turn out to be one chain:

1. **`show-actor` with a dummy follow button** — workstream 6 above.
2. **The left pane** — workstream 8 above.
3. **LinkedIn import** — `STRATEGIST.md`; unblocked, because there is now a real
   export to build against (Johan's own).
4. **Make the strategist act rather than analyse** — `STRATEGIST.md`.

The chain is 1 → 2 → 3, and it runs that way because of what LinkedIn is. A
LinkedIn export gives names, companies and titles and **no handles**, so its
output is candidate matches a human has to confirm — several hundred of them.
Confirming those in a chat transcript would be miserable (already logged as open
question 1 in `STRATEGIST.md`), so the import needs the pane. And what you
confirm is *a person*, so the pane needs a person card to show — which is
`show-actor`. Building the import first would mean building the confirm loop
twice.

(4) is orthogonal and cheap, and mostly a prompt change; do it whenever.

## Proposed sequencing

- **Phase 0** — this plan; agree direction and the open questions below.
- **Phase 1** — pick the target model; build a *minimal* eval harness with a
  handful of tasks, so every later change is measurable.
- **Phase 2** — write the steering doc + harden the tools, measuring against
  the harness as we go.
- **Phase 3** — grow the suite to ~20 tricky tasks; iterate.

(Measurement-first is a proposal, not a commitment — open to reordering.)

## Open questions (decide before Phase 1)

1. ~~**Target model.**~~ **DECIDED: `google/gemma-4-26b-a4b-it`** (26B total,
   ~4B active MoE — same model the `aligned` project uses). Driven via
   OpenRouter for now as a stand-in for running it locally later; same
   weights, so instruction work transfers. Set in `public/settings.json`.
2. **Steering-doc style.** Strict operating procedure (mechanical, minimal
   judgment) vs. principles (flexible, needs more model capability) vs.
   layered. Leaning strict for a weak model.
3. **Eval reproducibility.** Bluesky is live and changes under us. Do we
   snapshot/mock data for stable scoring, or design tasks robust to changing
   data? Affects how trustworthy the suite is. **Answered for binary decisions
   (2026-07-28): snapshot.** A match is scored against a frozen candidate
   profile, so a bio edit can't read as a regression; whether the right
   candidate was retrieved at all is measured separately and live. Open for
   everything else.
4. **Scoring.** Automated assertions (deterministic, limited) vs. an
   LLM-as-judge / rubric (flexible, needs a capable judge model) vs. a mix.
6. **Project layout.** Where do shared tools live (`tools/` vs `lib/` at
   root)? One agent-per-project vs. one agent + per-session `directory`? Exact
   permission ruleset for read-root/write-project (see design points above).
   Naming/location of project folders (all under repo root? a `projects/`
   dir?).
5. ~~**How the agent loads the steering doc.**~~ **DECIDED: `opencode.json`
   `instructions: ["OPERATING.md"]`**, resolved against opencode's project
   directory (verified it loads, separately from `AGENTS.md`; same file also
   sets the default model). Both files live in `agent/` beside the config that
   names them; AGENTS.md stays domain-only.

## Non-goals (for now)

- Making the agent "smart." We engineer around a weak model, not toward a
  strong one.
- Writing the steering doc or the eval tasks — those come after this plan is
  agreed.
