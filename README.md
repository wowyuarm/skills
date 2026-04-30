# yu-skills

Skills I created and refined for agent workflows.

See `AGENTS.md` for repository maintenance guidance.

## Skills

- [`ai-discussion-recap`](ai-discussion-recap/SKILL.md) — summarize useful recent discussion from local Claude Code, Codex, and Pi session logs
- [`deepwiki`](deepwiki/SKILL.md) — query DeepWiki documentation for public GitHub repositories over HTTP
- [`openclaw`](openclaw/SKILL.md) — answer OpenClaw questions using local docs, DeepWiki, and official site
- [`proxy-vps-ops`](proxy-vps-ops/SKILL.md) — manage the lifecycle of a self-hosted VPS used as a personal proxy node
- [`prune`](prune/SKILL.md) — repository inspection guidance for code-reading tasks
- [`repo-init`](repo-init/SKILL.md) — create `AGENTS.md` for a repository from its real files and conventions
- [`surfwind`](surfwind/SKILL.md) — drive the local Windsurf runtime through the `surfwind` CLI

## Notes

- Each top-level skill directory is self-contained.
- Validate the repository with `python3 scripts/validate_skills.py`.
- Local runtime state such as `proxy-vps-ops/references/current-state.local.md` is not committed.
