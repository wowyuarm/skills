# Skill Mechanics

The skill-specific branch of writing: frontmatter, the invocation choice, and this repository's index rules. The general writing rules (loads, pointers, hierarchy, leading words) live in [writing-great-skills.md](writing-great-skills.md). Adapted from mattpocock's `writing-for-agents` `SKILL-MECHANICS.md`; see [CREDITS.md](../CREDITS.md).

## Invocation

Two choices, trading the two loads:

- **Model-invoked** — keep the `description`. The agent can discover and run the skill on its own, and other skills can reach it. The description is a context pointer forced to stay permanently loaded: context load in exchange for discoverability. Model-invocation always *includes* user reach: a description only ever adds agent discovery, never removes the human's. Write the description agent-facing, carrying its trigger branches.
- **User-invoked** — set `disable-model-invocation: true`. Only the human typing the name can fire it, and no other skill can. Zero context load, but it spends cognitive load: you are the index that must remember it exists. The `description` becomes human-facing: one line, trigger lists stripped.

Pick model-invocation only when the agent must reach the skill on its own, or another skill must. If it only ever fires by hand, make it user-invoked and pay no context load.

In this repository, every skill declares its kind in frontmatter, appears under the matching `User-invoked` / `Model-invoked` heading in its group README and the top-level README, and carries `agents/openai.yaml` (`interface.display_name` and `interface.short_description`; user-invoked skills add `policy.allow_implicit_invocation: false`). The validator enforces all of this; keep the declarations and indexes in the same change.

## Splitting

Split a document only when the cut earns one of the loads:

- **By sequence** — split a run of steps when the later steps tempt the agent to rush the one in front of it (see completion criteria in [writing-great-skills.md](writing-great-skills.md)). Keeping the later steps out of view drives more legwork on the current one. Beware the reverse: merging sequences exposes each step's later steps, inviting premature completion.
- **By invocation** — split off a model-invoked skill when a distinct leading word you actually use should trigger it on its own, or another skill must reach it. The new always-loaded description must be worth its context load.

## Shared reference

Reference needed by several skills lives in one place. A model-invoked skill is a natural home: other skills can invoke it, so shared reference gets a single address (the way `tdd` leans on a shared vocabulary skill in mattpocock's set). Shared reference that two *user-invoked* skills both need can live in neither — with no descriptions, neither can fire the other. Push it to a plain file outside the skill system that any skill can point at.

## Routers

When user-invoked skills multiply past what you can remember, that piled-up cognitive load is cured by a **router**: one user-invoked skill that names the others and when to reach for each, so the human has one entry point to remember instead of many. It can only hint, never fire them: user-invoked skills have no description, so nothing but the human can reach them.
