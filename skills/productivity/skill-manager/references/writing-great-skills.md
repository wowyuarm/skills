# Writing Great Skills

A skill makes a method more predictable across future work. Keep the process stable; let judgment and output remain appropriate to the situation. These rules apply to any document an agent consumes — a `SKILL.md`, an `AGENTS.md`, a reference file — because the agent runs the same reading process each time. Adapted from mattpocock's `writing-for-agents`; see [CREDITS.md](../CREDITS.md).

## The two loads

Every document and every pointer spends one of two budgets:

- **Context load** — always-loaded material sitting in the agent's window every turn (a skill description, an `AGENTS.md` line). It costs tokens and attention whether or not it fires.
- **Cognitive load** — the human cost of knowing a document exists and when to reach for it. Not a cost to eliminate: it is the price of human agency. Spend it where human judgement matters, remove it where it does not.

Material reached only through a pointer escapes context load at the price of the pointer's own line. Material with no pointer rides entirely on cognitive load.

## Pointers

A **context pointer** names out-of-context material and encodes the condition for reaching it — a skill's `description`, or a line in `AGENTS.md` naming a doc. The pointer's *wording*, not its target, decides when the agent reaches the material and how reliably:

- Front-load the leading word; it does its triggering work first.
- One trigger per branch. Synonyms renaming a single case are one branch written twice; keep only genuinely distinct branches.
- Cut identity the body already carries.
- A must-have target behind a weakly worded pointer is a variance bug: sharpen the wording first, and inline the material only if sharpening fails.

## Information hierarchy

A document mixes two content types — **steps** (ordered actions the agent performs) and **reference** (definitions, rules, facts consulted on demand) — and each piece sits somewhere on a ladder ranked by how immediately the agent needs it:

1. **In-file step** — what the agent does, in order.
2. **In-file reference** — consulted on demand within the same file.
3. **Disclosed reference** — pushed to a separate file behind a pointer, loaded only when the pointer fires.

Push too little down and the top bloats; push too much and you hide material the agent actually needs. Branching is the cleanest disclosure test: inline what every branch needs, and push behind a pointer what only some branches reach.

- **Progressive disclosure** is the move down the ladder. It protects the hierarchy, not just tokens.
- **Co-location** keeps a concept's definition, rules, and caveats under one heading, so reading one part brings its neighbours with it. The test: the document should read like documentation written for the agent.
- **Sprawl** is the failure mode: a document simply too long, even when every line is live. Attention thins across the excess. The cure is the ladder: disclose reference behind pointers, split by branch or sequence.

## Completion criteria

Every step ends on a **completion criterion** — the condition that tells the agent the work is done. Two properties make it a lever:

- **Clarity**: can the agent tell done from not-done? A vague bound ("understanding reached") invites **premature completion**. The visible steps still ahead supply the pull; the criterion's clarity is the resistance. Sharpen the bound first (local and cheap); only if it is irreducibly fuzzy *and* you observe the rush, hide the later steps by splitting the sequence.
- **Demand**: how much it requires. "Every modified model accounted for" forces thorough work where "produce a change list" does not. Demand drives **legwork** — the digging latent in the wording rather than written as its own step. It binds flat reference too ("every rule applied"), which is how an all-reference document still carries an exhaustiveness bar.

The strongest criteria are both checkable and exhaustive.

## Leading words

A **leading word** is a compact concept already living in the model's pretraining that the agent thinks with while running the document (*seam*, *tracer bullet*, *fog of war*). Repeated as a token, never as a sentence, it anchors a whole region of behaviour in the fewest tokens by recruiting priors the model already holds. A made-up word recruits no priors: you pay in definition tokens what a pretrained word gives free. Reach for an existing word first, and coin your own only with a clear definition.

**Negation** is the failure mode beside this lever: steering by prohibition drags the forbidden behaviour into context and makes it *more* available (*don't think of an elephant*). Prompt the positive: state the target behaviour so the banned one is never spoken. A prohibition earns its place only as a hard guardrail you cannot phrase positively; even then, pair it with the positive target.

## Prune

- Keep each meaning in a **single source of truth**: one authoritative place, so changing the behaviour is a one-place edit. Duplication costs maintenance and inflates a meaning's prominence past its real rank.
- The **environment is a source of truth too** (`package.json` scripts, config files, `--help` output). A document restating it is a **cache**: a copy of a lookup, earning its load only when the lookup is expensive. Cache what the agent cannot find by looking — the unwritten convention, the reason behind a choice, the gotcha no config confesses. Leave one-command lookups to the environment, where they cannot go stale.
- Check every line for **relevance**: does it still bear on what the document does? Without a pruning discipline the default fate is **sediment** — stale layers that settle because adding feels safe and removing feels risky.

A skill should carry only the knowledge that changes how the next agent can work.
