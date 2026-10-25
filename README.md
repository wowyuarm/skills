# yu-skills

Skills I created and refined for agent workflows.

See `AGENTS.md` for repository maintenance guidance.

## Skills

Skills live under `skills/` in two groups: `engineering/` for daily code work and `productivity/` for daily non-code workflow. Entries are grouped by how they are reached: **User-invoked** skills fire only when the human types their name (`disable-model-invocation: true`); **Model-invoked** skills the agent may also discover and run on its own.

### Engineering

#### Model-invoked

- [`codebase-ablation`](skills/engineering/codebase-ablation/SKILL.md) — measure a module's real load-bearing role by deleting or stubbing it and running the test suite; coupling map, blast radius, hidden-dependency detection
- [`deepwiki`](skills/engineering/deepwiki/SKILL.md) — query DeepWiki documentation for public GitHub repositories over HTTP
- [`repo-init`](skills/engineering/repo-init/SKILL.md) — create `AGENTS.md` for a repository from its real files and conventions

### Productivity

#### User-invoked

- [`bilibili-custom-feeds`](skills/productivity/bilibili-custom-feeds/SKILL.md) — build and tune a personal, rule-authored Bilibili feed as a Tampermonkey userscript running in your own logged-in browser
- [`machine-identity-reset`](skills/productivity/machine-identity-reset/SKILL.md) — reset an AI CLI or desktop app's local identity (device IDs, fingerprints, credentials) while keeping your own config
- [`proxy-vps-ops`](skills/productivity/proxy-vps-ops/SKILL.md) — manage the lifecycle of a self-hosted VPS used as a personal proxy node

#### Model-invoked

- [`ai-discussion-recap`](skills/productivity/ai-discussion-recap/SKILL.md) — summarize useful recent discussion from local Claude Code, Codex, and Pi session logs
- [`skill-manager`](skills/productivity/skill-manager/SKILL.md) — create, install, revise, or retire agent skills across harnesses, including skill-local configuration and credentials

## Notes

- Each skill directory is self-contained.
- Validate the repository with `python3 scripts/validate_skills.py`.
- Local runtime state such as `skills/productivity/proxy-vps-ops/references/current-state.local.md` is not committed.
- Retired skills live in `archive/` (local only, not tracked).

## Acknowledgements

The organization of this repository — skill groups under `skills/`, index discipline, the User-invoked / Model-invoked distinction, and mechanical gating via the validator — follows the approach of [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). Individual skills adapted from that repository keep a `CREDITS.md` in their own directory recording the source path and original license.
