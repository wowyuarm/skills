---
name: prune
description: Use for repository-understanding work when inspection should go through prune instead of raw grep/cat/find. Covers when to survey, how to search multiple likely paths, how to choose read --start vs --around, how to inspect diffs, and how to stop once evidence is sufficient.
---

# Prune Skill

Use this when the job is to understand a repository, trace a code path, find the right files, or gather enough evidence to answer a question.

`prune` is not a shell replacement. Use it as the default tool for inspection, and keep bash for execution, tests, installs, and other non-inspection work.

## Pick the smallest useful command

- Use `prune survey` when you do not yet know where the relevant code probably lives.
- Skip `survey` when the likely file, directory, or hotspot is already known from the user prompt or from an earlier step.
- Use `prune search <pattern> [PATH ...]` to narrow quickly once you have one or more likely locations.
- Use `prune read` when you already know the file and want bounded context.
- Use `prune diff` when the question is about local changes rather than repository structure.
- Use `prune batch` only when the next few inspection steps are already obvious and short.

## Search well

- Pass several likely files or directories to one `prune search` instead of broadening to the whole repo too early.
- Start with literal search when the pattern is plain text. Retry once with `--regex` when the pattern needs structure or the literal search misses.
- Prefer one well-aimed `prune search` over shell-chaining several searches with `&&`. If you need two related text checks, first ask whether one regex search or one bounded read would settle it.
- Narrow noisy output with `--file-type`, `--group-depth`, `--budget`, and `--ignore` before falling back to raw commands.
- Once search tells you the likely file and line, stop searching and switch to `read`.
- If you already know the exact short chain, you may package it as one `prune batch` run instead of repeating separate inspection calls.

## Read the right slice

- `prune read` takes exactly one file. If you need several known file reads, use `prune batch` with multiple `read` steps or run separate `prune read` commands.
- Use `prune read <file> --start <line> --lines <count>` when you know the line and want to move forward through the code.
- Use `prune read <file> --around <line> --lines <count>` when you want centered context around one hit.
- Use `prune read <file> --section end --lines <count>` when the interesting material is likely at the bottom of the file, such as tests or trailing helpers.
- Prefer a few bounded reads over dumping large files.

## Inspect changes cleanly

- `prune diff` accepts at most one optional path argument. For several changed files, use `prune diff . --stat` or `prune diff <shared-directory>` and then inspect the top files with `prune read`.
- Do not treat `prune diff <file>` as a per-file patch viewer. Use `prune diff` for repository or directory summaries, then switch to `prune read` for file context; only use raw `git diff -- <file>` when you truly need the literal patch.
- Use `prune diff` before raw patches when you need to understand what changed.
- Use `prune diff --stat` when you only need shape, not hunk detail.
- Follow `diff` with `read` on the top changed files instead of opening the whole patch immediately.

## Use batch carefully

- `prune batch` is for explicit short inspection plans, not for open-ended exploration.
- Keep each step simple and inspection-only: `survey`, `search`, `read`, or `diff`.
- In `prune batch --plan`, each step must use only fields valid for that command. Do not invent fields like `search` inside a `read` step; if you need different actions, create separate batch steps.
- Do not use batch to hide uncertainty. If you do not know where to look yet, use a normal single command first.
- Prefer plans that reduce repeated turns such as `search -> read` or `diff -> read`.
- When you already know the short chain, prefer the inline form first: `prune batch --plan '<json>'`.
- Natural JSON shapes are accepted too: a top-level array is fine, `cmd` works as an alias for `command`, `search.path` works as shorthand for a single `search.paths` entry, `read.path` works as an alias for `read.file`, and nested step objects like `{"cmd":"read","read":{"path":"src/main.rs"}}` are accepted.
- If the task already names exact files and line hints, prefer one small `read`-heavy batch first instead of opening with extra searches.
- After a read-heavy batch, pause and check whether the answer is already supported before adding more reads or searches.
- Treat a batch failure as a useful signal. Fix the plan or switch back to one-step inspection instead of trying to hide the error.

## Efficiency rules

- Prefer one narrow search plus one or two targeted reads over repeated repo-wide scans.
- Avoid reopening the same file with heavily overlapping windows unless a red flag is still unresolved.
- Do not chain `prune` inspection commands with shell operators unless `prune` truly cannot express the step cleanly.
- After each step, decide whether the answer is already supported.
- Once you have enough direct evidence to answer the question cleanly, stop instead of continuing to browse for completeness.
- When using batch, preserve the same discipline: fewer turns is good, but not at the cost of skipping the evidence.

## Fallback

- If `prune` cannot express the inspection you need, use the smallest raw command that does.
