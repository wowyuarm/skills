---
name: repo-init
description: Initialize a repository that does not yet have an AGENTS.md contributor guide. Use when an agent needs to inspect an unfamiliar codebase, extract its real build/test/run conventions, and write a concise repository guide without inventing commands, architecture, or policies.
---

Create `AGENTS.md` only when the repository does not already have one.

## Map the repository before writing

- Read the top-level tree first.
- Read the smallest authoritative files that define the repo contract:
  `README.md`, build manifests, test config, lint config, and architecture docs.
- Infer the tech stack from real files such as `Cargo.toml`, `package.json`,
  `pyproject.toml`, `go.mod`, `Makefile`, or CI config.
- Prefer exact commands already used by the repo over generic ecosystem defaults.

## Extract only durable contributor knowledge

Capture the information another agent or contributor needs to work safely:

- project purpose and scope
- top-level directory responsibilities
- build, test, lint, type-check, run, debug, and deploy commands
- naming and formatting conventions
- testing layout and expectations
- security, configuration, and secret-handling rules
- architectural boundaries and agent guardrails

If the repository does not expose a fact clearly, write `> TODO:` instead of
inventing it.

## Write the guide for fast reuse

- Title the file `Repository Guidelines` unless the user asks otherwise.
- Keep the document concise, specific, and instructional.
- Use Markdown headings and short bullet lists.
- Preserve exact command spellings from the repo.
- Prefer concrete paths like `src/`, `tests/`, and `docs/` over vague prose.

## Recommended section order

1. Project Overview
2. Repository Structure
3. Build & Development Commands
4. Code Style & Conventions
5. Architecture Notes
6. Testing Strategy
7. Security & Compliance
8. Agent Guardrails
9. Extensibility Hooks
10. Further Reading

Drop sections that truly do not apply, but keep the output easy to scan.

## Validation checklist

- Confirm `AGENTS.md` did not already exist.
- Confirm every listed command came from the repo or is clearly marked `> TODO:`.
- Confirm the guide matches the repository's actual boundaries.
- Confirm the result is useful to both humans and other agents.
