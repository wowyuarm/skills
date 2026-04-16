# Repository Guidelines

## Project Overview

- `yu-skills` is a source repository of reusable agent skills.
- Each top-level directory with a `SKILL.md` file is a self-contained skill.
- Keep `README.md` short and human-oriented; put maintenance guidance here.

## Repository Structure

- `*/SKILL.md` — required skill entry file with frontmatter and instructions
- `*/references/` — stable supporting docs
- `*/scripts/` — deterministic helper scripts
- `*/assets/` — templates or static files
- `*/agents/` — harness-specific metadata when needed
- `scripts/validate_skills.py` — repo-wide validator

Current top-level skills:
- `ai-discussion-recap/`
- `deepwiki/`
- `proxy-vps-ops/`
- `prune/`
- `repo-init/`
- `surfwind/`

Keep this list in sync with the actual top-level skill directories.
If you add, remove, rename, or install a skill in this repository, update the skill indexes in both `README.md` and `AGENTS.md` in the same change.

## Build & Development Commands

- Validate the repository: `python3 scripts/validate_skills.py`
- No other repo-wide build, test, or lint command is currently defined.

## Code Style & Conventions

- Keep skills self-contained and concise.
- Match each skill directory name to the frontmatter `name` in `SKILL.md`.
- Put durable guidance in `references/`; do not bloat `SKILL.md` with large supporting docs.
- Put repeatable helper logic in `scripts/`.
- If you add shell scripts, they must parse under `bash -n`.
- Prefer harness-agnostic skill structure unless a harness-specific file is clearly needed.

## Architecture Notes

- The validator discovers skills by scanning top-level directories for `SKILL.md`.
- The repository is meant to stay generally reusable across Pi, Claude Code, Codex-style harnesses, and similar environments.
- `deepwiki/agents/openai.yaml` is an example of optional harness-specific metadata.
- `proxy-vps-ops` separates stable guidance from runtime state:
  - tracked: `proxy-vps-ops/references/current-state.template.md`
  - local only: `proxy-vps-ops/references/current-state.local.md`

## Testing Strategy

- Run `python3 scripts/validate_skills.py` after changing `SKILL.md`, repository layout, or helper scripts.
- There is no broader automated test suite yet.

## Security & State Handling

- Do not commit secrets, host-specific credentials, or machine-specific notes.
- Do not commit local runtime ledgers such as `**/references/current-state.local.md`.
- When a skill needs mutable state, commit a template and ignore the live local file.

## Agent Guardrails

- Do not invent repo-wide commands, CI, packaging, or release workflow that the repository does not define.
- Prefer small, targeted edits over broad rewrites.
- Preserve existing skill paths unless the user explicitly wants a reorganization.
- When adding new instructions, keep them durable and reusable rather than session-specific.

## Extensibility Hooks

- Add a new skill as a new top-level directory containing `SKILL.md`.
- Optional per-skill directories are `references/`, `scripts/`, `assets/`, and `agents/`.
- If a new skill needs local mutable state, follow the template-plus-local-file pattern already used by `proxy-vps-ops`.
- After adding, removing, renaming, or installing a skill here, update the top-level skill index in `README.md` and the maintained skill list in `AGENTS.md`.

## Further Reading

- `README.md`
- `scripts/validate_skills.py`
- `repo-init/SKILL.md`
- `proxy-vps-ops/SKILL.md`
