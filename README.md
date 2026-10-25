# yu-skills

Skills I created and refined for agent workflows.

See `AGENTS.md` for repository maintenance guidance.

## Skills

Skills live under `skills/` in two groups: `engineering/` for daily code work and `productivity/` for daily non-code workflow. Entries are grouped by how they are reached: **User-invoked** skills fire only when the human types their name (`disable-model-invocation: true`); **Model-invoked** skills the agent may also discover and run on its own.

### Engineering

#### User-invoked

- [`ax-init`](skills/engineering/ax-init/SKILL.md) — initialize or retrofit a repository's agent layer: short root `AGENTS.md`, `.scratch/` work area, optional `docs/` skeleton
- [`ax-review`](skills/engineering/ax-review/SKILL.md) — audit a repository's agent experience: mechanical link/reference checks plus a simulated cold-start walk

#### Model-invoked

- [`codebase-ablation`](skills/engineering/codebase-ablation/SKILL.md) — measure a module's real load-bearing role by deleting or stubbing it and running the test suite; coupling map, blast radius, hidden-dependency detection
- [`deepwiki`](skills/engineering/deepwiki/SKILL.md) — query DeepWiki documentation for public GitHub repositories over HTTP
- [`diagnosing-bugs`](skills/engineering/diagnosing-bugs/SKILL.md) — hard-bug diagnosis loop: build a tight red-capable feedback loop first, then reproduce, hypothesise, instrument, fix, clean up
- [`domain-modeling`](skills/engineering/domain-modeling/SKILL.md) — build and sharpen a project's domain model: glossary discipline, edge-case scenarios, sparing ADRs
- [`research`](skills/engineering/research/SKILL.md) — investigate a question against high-trust primary sources and capture the findings as a cited Markdown file
- [`tdd`](skills/engineering/tdd/SKILL.md) — test-driven development: red-green loop at pre-agreed seams, with what a good test is and the anti-patterns

### Productivity

#### User-invoked

- [`bilibili-custom-feeds`](skills/productivity/bilibili-custom-feeds/SKILL.md) — build and tune a personal, rule-authored Bilibili feed as a Tampermonkey userscript running in your own logged-in browser
- [`machine-identity-reset`](skills/productivity/machine-identity-reset/SKILL.md) — reset an AI CLI or desktop app's local identity (device IDs, fingerprints, credentials) while keeping your own config
- [`proxy-vps-ops`](skills/productivity/proxy-vps-ops/SKILL.md) — manage the lifecycle of a self-hosted VPS used as a personal proxy node

#### Model-invoked

- [`ai-discussion-recap`](skills/productivity/ai-discussion-recap/SKILL.md) — summarize useful recent discussion from local Claude Code, Codex, and Pi session logs
- [`grilling`](skills/productivity/grilling/SKILL.md) — stress-test a plan or decision relentlessly: interview in frontier rounds until nothing is silently assumed
- [`skill-manager`](skills/productivity/skill-manager/SKILL.md) — create, install, revise, or retire agent skills across harnesses, including skill-local configuration and credentials

## Notes

- Each skill directory is self-contained.
- Validate the repository with `python3 scripts/validate_skills.py`.
- Local runtime state such as `skills/productivity/proxy-vps-ops/references/current-state.local.md` is not committed.
- Retired skills live in `archive/` (local only, not tracked).

## Acknowledgements

The organization of this repository — skill groups under `skills/`, index discipline, the User-invoked / Model-invoked distinction, and mechanical gating via the validator — follows the approach of [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). Individual skills adapted from that repository keep a `CREDITS.md` in their own directory recording the source path and original license.
