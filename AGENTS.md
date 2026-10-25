# Repository Guidelines

## Project Overview

- `yu-skills` is a source repository of reusable agent skills.
- Skills live under `skills/` in domain groups; each skill directory with a `SKILL.md` file is self-contained.
- Keep `README.md` short and human-oriented; put maintenance guidance here.

## Repository Structure

```
skills/
  engineering/    — daily code work
  productivity/   — daily non-code workflow
archive/          — retired skills, local only (not tracked)
scripts/          — repo-wide tooling
```

Per-skill layout:

- `*/SKILL.md` — required skill entry file with frontmatter and instructions
- `*/references/` — stable supporting docs
- `*/scripts/` — deterministic helper scripts
- `*/assets/` — templates or static files
- `*/agents/` — harness-specific metadata (`openai.yaml`, required; see Architecture Notes)
- `scripts/validate_skills.py` — aggregate runner for the checks in `scripts/checks/`
- `scripts/checks/` — atomic checks, one concern per script, each runnable on its own

Current skills:

- `skills/engineering/codebase-ablation/`
- `skills/engineering/deepwiki/`
- `skills/engineering/diagnosing-bugs/`
- `skills/engineering/domain-modeling/`
- `skills/engineering/research/`
- `skills/engineering/tdd/`
- `skills/engineering/ax-init/`
- `skills/engineering/ax-review/`
- `skills/productivity/ai-discussion-recap/`
- `skills/productivity/grilling/`
- `skills/productivity/bilibili-custom-feeds/`
- `skills/productivity/machine-identity-reset/`
- `skills/productivity/proxy-vps-ops/`
- `skills/productivity/skill-manager/`

Keep this list in sync with the actual skill directories.
If you add, remove, rename, or move a skill, update the skill indexes in the group `README.md`, the top-level `README.md`, and this list in the same change.

## Invocation

Every skill is one of two kinds, declared in `SKILL.md` frontmatter:

- **User-invoked**: `disable-model-invocation: true`. Fires only when the human types its name; the `description` is human-facing, one line, no trigger lists.
- **Model-invoked**: no `disable-model-invocation` (or `false`). The agent may discover and run it on its own; the `description` is agent-facing and carries its trigger conditions.

A group may mix both kinds. Group READMEs and the top-level README group entries under `User-invoked` / `Model-invoked` headings; omit a heading when it has no entries.

## Index Discipline

- Each group directory has a `README.md` listing every skill in it: one line each, skill name linked to its `SKILL.md`, plus a one-line description.
- The top-level `README.md` links every skill under `skills/`.
- Indexes and skill directories are verified against each other by the validator; both directions must match.

## Build & Development Commands

- Validate the repository: `python3 scripts/validate_skills.py`
- No other repo-wide build, test, or lint command is currently defined.

## Mechanical Gating

Structure is enforced by `python3 scripts/validate_skills.py`, which runs every atomic check under `scripts/checks/` (each `check_*.py` is independently runnable and owns one concern; shared discovery and parsing live in `scripts/checks/_common.py`). The checks verify:

- Every `skills/*/*/SKILL.md` has valid frontmatter with `name` and `description`; `name` matches the directory name.
- Every skill under `skills/` appears in its group README and the top-level README, and every indexed link resolves to a real skill.
- Skills listed under a `User-invoked` heading have `disable-model-invocation: true`; skills under `Model-invoked` do not.
- Every skill has `agents/openai.yaml` with non-empty `interface.display_name` and `interface.short_description`.
- Shell scripts under `*/scripts/` parse under `bash -n`.
- Runtime state files (`*/references/current-state.local.md`) are flagged with a warning.

Run the validator after any change to `SKILL.md` files, layout, indexes, or scripts. Add a new gate as a new `check_*.py` script; the runner picks it up automatically.

## Code Style & Conventions

- Keep skills self-contained and concise.
- Match each skill directory name to the frontmatter `name` in `SKILL.md`.
- Put durable guidance in `references/` or sibling reference files; do not bloat `SKILL.md` with large supporting docs.
- Put repeatable helper logic in `scripts/`.
- Keep skill structure harness-agnostic apart from the standard `agents/openai.yaml` metadata file.

## Architecture Notes

- The validator discovers skills by scanning `skills/*/*/SKILL.md`.
- The repository is meant to stay generally reusable across Pi, Claude Code, Codex-style harnesses, and similar environments.
- `agents/openai.yaml` carries the metadata Codex/OpenAI-style harnesses read: `interface.display_name` and `interface.short_description` are required for every skill; a User-invoked skill additionally sets `policy.allow_implicit_invocation: false`; extra keys such as `deepwiki`'s `default_prompt` are allowed. Claude Code and Pi ignore this file and read only the frontmatter.
- `proxy-vps-ops` separates stable guidance from runtime state:
  - tracked: `skills/productivity/proxy-vps-ops/references/current-state.template.md`
  - local only: `skills/productivity/proxy-vps-ops/references/current-state.local.md`

## Testing Strategy

- Run `python3 scripts/validate_skills.py` after changing `SKILL.md`, repository layout, or helper scripts.
- There is no broader automated test suite yet.

## Security & State Handling

- Do not commit secrets, host-specific credentials, or machine-specific notes.
- Do not commit local runtime ledgers such as `**/references/current-state.local.md`.
- When a skill needs mutable state, commit a template and ignore the live local file.

### Sanitization

Skills are published. Anything written into a tracked file is public, so treat
examples as documentation for strangers rather than a transcript of this machine.

Use placeholders for anything that identifies a person or a host:

| Instead of | Write |
| --- | --- |
| a real home path, e.g. `/home/alice/projects/api` | `/home/<user>/projects/<repo>` |
| a real Windows path, e.g. `C:\Users\alice\...` | `C:\Users\<user>\...` |
| a real device ID, account UUID, or machine ID | `<device-id>`, `<account-uuid>`, `<machine-id>` |
| a real email, hostname, or public IP | `<email>`, `<host>`, `<ip>` |
| a real API key or token | a placeholder, or `$ENV_VAR` |

Slug and path transformations are the useful part of an example; the concrete
path is not. Show the rule (`/home/<user>/a/b` → `-home-<user>-a-b`), not the
path it was derived from.

Some values look identifying but are not personal — a constant baked into a
third-party tool is the same for every user of that tool. Check what a value is
before replacing it; genericizing a shared constant makes the document wrong
without making it safer.

Credentials belong in a skill-local `auth.json` (ignored), read at run time; see
`skills/productivity/skill-manager/SKILL.md`. Environment variables and CLI
arguments are acceptable alternatives when the credential is supplied per run.

Before committing, grep the staged content for the patterns above. A value that
only ever appeared in local-only files is already covered by `.gitignore`; a
value in a tracked file is not.

## Borrowed Skills

- The repository organization follows [mattpocock/skills](https://github.com/mattpocock/skills) (MIT); the top-level `README.md` carries the acknowledgement.
- A skill adapted from another repository keeps a `CREDITS.md` in its own directory recording the source repository, the source path, and the original license.

## Agent Guardrails

- Do not invent repo-wide commands, CI, packaging, or release workflow that the repository does not define.
- Prefer small, targeted edits over broad rewrites.
- Preserve existing skill paths unless the user explicitly wants a reorganization.
- When adding new instructions, keep them durable and reusable rather than session-specific.

## Git Commit Discipline

- Commit every modification, even small ones. Do not leave uncommitted changes in the working tree.
- Commit each batch of changes separately, grouped by topic and time.
- Use `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` to match the actual file modification timestamps (from `stat`), so the commit history reflects when the work happened, not when you happened to run `git commit`.
- Use meaningful commit messages: `<skill-name>: <what changed>` (repo-wide changes use `repo:`). Keep messages short but specific enough to understand without reading the diff.
- After adding, removing, renaming, or moving a skill, update the group README, the top-level `README.md`, and the maintained skill list in `AGENTS.md` in the same commit.

## Extensibility Hooks

- Add a new skill as `skills/<group>/<skill-name>/` containing `SKILL.md`.
- Optional per-skill directories are `references/`, `scripts/`, `assets/`, and `agents/`.
- If a new skill needs local mutable state, follow the template-plus-local-file pattern already used by `proxy-vps-ops`.
- Retire a skill by moving it to `archive/` (untracked) and removing its index entries in the same change.

## Further Reading

- `README.md`
- `scripts/validate_skills.py`
- `skills/engineering/ax-init/SKILL.md`
- `skills/productivity/proxy-vps-ops/SKILL.md`
- `skills/productivity/skill-manager/SKILL.md`
