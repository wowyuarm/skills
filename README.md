# yu-skills

Skills I created and refined for agent workflows.

See `AGENTS.md` for repository maintenance guidance.

## Skills

- [`ai-discussion-recap`](ai-discussion-recap/SKILL.md) — summarize useful recent discussion from local Claude Code, Codex, and Pi session logs
- [`codebase-ablation`](codebase-ablation/SKILL.md) — measure a module's real load-bearing role by deleting or stubbing it and running the test suite; coupling map, blast radius, hidden-dependency detection
- [`deepwiki`](deepwiki/SKILL.md) — query DeepWiki documentation for public GitHub repositories over HTTP
- [`proxy-vps-ops`](proxy-vps-ops/SKILL.md) — manage the lifecycle of a self-hosted VPS used as a personal proxy node
- [`repo-init`](repo-init/SKILL.md) — create `AGENTS.md` for a repository from its real files and conventions
- [`skill-manager`](skill-manager/SKILL.md) — create, install, revise, or retire agent skills across harnesses, including skill-local configuration and credentials

## Notes

- Each top-level skill directory is self-contained.
- Validate the repository with `python3 scripts/validate_skills.py`.
- Local runtime state such as `proxy-vps-ops/references/current-state.local.md` is not committed.
