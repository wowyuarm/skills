---
name: ax-init
description: Initialize or retrofit a repository's agent-experience (ax) layer - a short root AGENTS.md that carries only always-on rules and routes everything else, a .scratch/ cross-session work area with ticket discipline, and an optional docs/ skeleton (docs/AGENTS.md + docs/README.md routing index). Use when setting up a repo for agent work, when an agent lands in a repo without this layer, or when the user asks to initialize a repo, bootstrap AGENTS.md, set up docs or .scratch, 搭骨架, 初始化项目.
---

# ax-init

`ax` = agent experience: the layer an agent needs to work in a repository across sessions. This skill builds it:

| Piece | Role | Default |
| --- | --- | --- |
| Root `AGENTS.md` | Only the rules every task must know, plus routing. Loaded into every session, so it stays short (~60 lines) | always |
| `.scratch/` | Cross-session work items: design snapshots, research, tickets, validation evidence — never an authority on current behavior | always |
| `docs/` skeleton | Maintained engineering docs: `docs/README.md` routing index + `docs/AGENTS.md` maintenance discipline | only when the repo warrants maintained docs |

The pattern is proven in real agent-driven repositories (Loom, dsh-agent-team): a fat root guide drowns every session, so the root file routes instead of explaining; in-progress work lives in `.scratch/active/` where it can change hourly without polluting history; durable conclusions graduate into `docs/` when the work closes.

## Map the repository before writing

- Read the top-level tree, then the smallest authoritative files: `README.md`, build manifests, test and lint config, existing architecture docs.
- Infer the stack from real files (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `Makefile`, CI config); prefer exact commands the repo already uses over ecosystem defaults.
- Extract only durable contributor knowledge: purpose and scope, top-level directory responsibilities, build/test/lint/run commands, conventions, boundaries, secret-handling rules.
- If the repo does not expose a fact, write `> TODO:` — never invent commands, architecture, or policies.

## Write the root AGENTS.md

Short by design. Five parts, in this order:

1. **Scope and authority** — what this repository is, in one short paragraph, then the authority order: source and tests define current behavior; maintained `docs/` explains it; `.scratch/` is work history and never overrides either.
2. **Reading discipline** — start from the files a task names, expand by need, do not read the whole repo; route through `docs/README.md` when it exists.
3. **Always-on constraints** — at most ~8 rules every task genuinely needs: the build/test entrypoints, the few architecture guardrails that are easy to violate, commit discipline.
4. **Pointers** — one line each for `docs/AGENTS.md` (if present) and `.scratch/AGENTS.md`.
5. Nothing else. Long structure maps, per-command detail, and research history belong in `docs/` and `.scratch/`, not in the file every session loads.

Write it in the repository's dominant documentation language (translate the headings; keep technical terms as-is).

## Create the .scratch work area

Copy `assets/<lang>/scratch-AGENTS.md` to `.scratch/AGENTS.md` and `assets/<lang>/scratch-README.md` to `.scratch/README.md`, adapting the prose the way you would adapt any boilerplate: drop what does not apply, keep the discipline. The templates define the work-item structure (`active/<work>/` with a five-item continuation README, `DESIGN.md`, `issues/NN-<slug>.md` tickets), ticket discipline (vertical slices, self-contained, frontier workflow), the closing lifecycle, and git tracking. Do not rewrite these rules per repo unless the repo genuinely works differently — their value is being the same everywhere.

Add to `.gitignore` (create the entries; keep the file's existing content):

```gitignore
.scratch/active/
.scratch/local/
```

Create the directories `active/` and `local/` (empty; `local/` is ignored anyway).

## Add the docs skeleton when warranted

Skip it for small repos — a root file plus `.scratch/` is enough, and an empty routing index pointing at nothing is worse than no index. Create it when the repo already has (or will soon grow) multiple maintained docs — architecture pages, runbooks, domain models:

- `assets/<lang>/docs-README.md` → `docs/README.md`: task-based routing table ("you want to do X → read Y") plus a fact-ownership table (which document owns which class of fact). Fill rows from the repo's real documents; two honest rows beat ten stub rows.
- `assets/<lang>/docs-AGENTS.md` → `docs/AGENTS.md`: maintenance discipline — one fact one home, a change that invalidates a documented fact updates the owning document in the same change, uncertain facts as `> TODO:`, no empty shells for modules that do not exist.

Do not pre-create empty subsystem pages. The skeleton is governance, not filler.

## Retrofit an existing AGENTS.md

Never overwrite an existing root `AGENTS.md`. When one exists, read it, separate always-on rules from long-form explanation, and propose the restructure: rules stay in the root file, explanation moves to `docs/` pages (create the skeleton in the same pass if it is missing), work-history notes move to `.scratch/`. Apply it only with the user's go-ahead, since the existing file may be load-bearing for other tooling.

## Validation checklist

- Every command in the generated files comes from the repo or is marked `> TODO:`.
- Root `AGENTS.md` fits on one screen and contains no content that belongs in `docs/` or `.scratch/`.
- `.scratch/AGENTS.md` and `.scratch/README.md` exist; `.gitignore` covers `active/` and `local/`.
- If `docs/` was created, every routing row points at a file that exists.
- All generated files use the repository's dominant documentation language consistently.
