# Engineering

Skills for daily code work.

Entries are grouped by how they are reached: **User-invoked** skills fire only when the human types their name (`disable-model-invocation: true`); **Model-invoked** skills the agent may also discover and run on its own.

## Model-invoked

- [`codebase-ablation`](codebase-ablation/SKILL.md) — measure a module's real load-bearing role by deleting or stubbing it and running the test suite; coupling map, blast radius, hidden-dependency detection
- [`deepwiki`](deepwiki/SKILL.md) — query DeepWiki documentation for public GitHub repositories over HTTP
- [`ax-init`](ax-init/SKILL.md) — initialize or retrofit a repository's agent layer: short root `AGENTS.md`, `.scratch/` work area, optional `docs/` skeleton
