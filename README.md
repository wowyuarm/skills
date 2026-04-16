# yu-skills

Personal but shareable collection of reusable Agent Skills.

This repository is kept **harness-agnostic first**. Each top-level directory is a self-contained skill folder built around the Agent Skills model:
- `SKILL.md` for trigger metadata and instructions
- optional `references/` for stable supporting docs
- optional `scripts/` for deterministic helpers
- optional `assets/` for templates or other files

The goal is to keep the skills useful across Pi, Claude Code, Codex-style harnesses, and any other environment that can consume skill directories.

## Repository Layout

```text
yu-skills/
├── ai-discussion-recap/
├── deepwiki/
├── proxy-vps-ops/
├── prune/
├── repo-init/
├── surfwind/
└── scripts/
    └── validate_skills.py
```

## Runtime State Convention

Stable knowledge belongs in the repository.

Per-engagement runtime state does **not**.

If a skill needs a working ledger, use this pattern:
- track a shareable template such as `references/current-state.template.md`
- write live state into `references/current-state.local.md`
- keep the local state file out of git

Current example:
- `proxy-vps-ops/references/current-state.template.md` is tracked
- `proxy-vps-ops/references/current-state.local.md` is local-only

## Using The Skills

### Pi

Load the repository root through the `skills` setting:

```json
{
  "skills": ["/absolute/path/to/yu-skills"]
}
```

Or point at a specific skill directory if you only want one.

### Claude Code / Codex-style harnesses

Use whichever mechanism the harness supports:
- add the repository root as an extra skills directory
- or symlink individual skill folders into the harness-specific skill directory

Examples:

```bash
ln -s ~/projects/yu-skills/proxy-vps-ops ~/.claude/skills/proxy-vps-ops
ln -s ~/projects/yu-skills/proxy-vps-ops ~/.codex/skills/proxy-vps-ops
```

### Generic usage

Clone the repository and point your harness to either:
- the repository root for all top-level skills
- a specific skill directory for targeted use

## Authoring Rules

- Keep skills self-contained.
- Keep `SKILL.md` concise and action-oriented.
- Put durable, stable guidance in `references/`.
- Put repeatable deterministic actions in `scripts/`.
- Do not commit local engagement state.
- Prefer shareable defaults and templates over machine-specific notes.

## Validation

Run:

```bash
python3 scripts/validate_skills.py
```

The validator checks basic repository hygiene:
- every discovered `SKILL.md` has frontmatter
- `name` matches the parent directory
- `description` is present
- shell scripts under skill directories parse with `bash -n`
- local runtime-state files are ignored by default convention

If `PyYAML` is installed, the validator also performs full YAML frontmatter parsing.

## Sharing

This repository is intended to be shareable, but it currently has no explicit license.

If you plan to publish it publicly, add a license first.
