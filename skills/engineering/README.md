# Engineering

Skills for daily code work.

Entries are grouped by how they are reached: **User-invoked** skills fire only when the human types their name (`disable-model-invocation: true`); **Model-invoked** skills the agent may also discover and run on its own.

## User-invoked

- [`ax-init`](ax-init/SKILL.md) — initialize or retrofit a repository's agent layer: short root `AGENTS.md`, `.scratch/` work area, optional `docs/` skeleton
- [`ax-review`](ax-review/SKILL.md) — audit a repository's agent experience: mechanical link/reference checks plus a simulated cold-start walk

## Model-invoked

- [`codebase-ablation`](codebase-ablation/SKILL.md) — measure a module's real load-bearing role by deleting or stubbing it and running the test suite; coupling map, blast radius, hidden-dependency detection
- [`deepwiki`](deepwiki/SKILL.md) — query DeepWiki documentation for public GitHub repositories over HTTP
- [`diagnosing-bugs`](diagnosing-bugs/SKILL.md) — hard-bug diagnosis loop: build a tight red-capable feedback loop first, then reproduce, hypothesise, instrument, fix, clean up
- [`domain-modeling`](domain-modeling/SKILL.md) — build and sharpen a project's domain model: glossary discipline, edge-case scenarios, sparing ADRs
- [`research`](research/SKILL.md) — investigate a question against high-trust primary sources and capture the findings as a cited Markdown file
- [`tdd`](tdd/SKILL.md) — test-driven development: red-green loop at pre-agreed seams, with what a good test is and the anti-patterns
