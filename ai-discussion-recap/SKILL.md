---
name: ai-discussion-recap
description: Summarize important recent AI collaboration discussions from local Claude Code, Codex, and Pi session logs, especially when the user asks to review recent project decisions, architectural debates, agreed principles, major refactors, or next-step conclusions preserved in ~/.claude/projects/..., ~/.codex/sessions/..., and ~/.pi/agent/sessions/.... Use when assistant needs to inspect conversation history, filter noisy tool events or injected setup messages, and produce a concise recap of the meaningful user and assistant discussion.
---

# AI Discussion Recap

Use this skill when the user wants a recap of recent Claude Code, Codex, or Pi discussions that matter to project direction, such as large adjustments, architecture choices, working principles, implementation plans, or important conclusions that may otherwise be forgotten.

## Workflow

1. Resolve the relevant conversation store:
   Claude Code under `~/.claude/projects/`
   Codex under `~/.codex/sessions/`
   Pi under `~/.pi/agent/sessions/`
2. Use `scripts/extract_ai_discussions.py` to list recent candidate sessions for the current repo or an explicitly provided project path.
3. Read the extracted markdown or JSON output first. Open raw JSONL files only for the most relevant sessions.
4. Summarize the discussion into decisions, reasoning, open questions, and next steps.
5. Quote sparingly. Prefer short excerpts and clear synthesis.

## Subagent Pattern

If subagents are available, prefer delegating the candidate-session scan as a side task while you keep the main thread focused on synthesis.

Give the subagent a bounded task:

- identify the relevant project path and whether Claude, Codex, Pi, or all sources should be scanned
- run `scripts/extract_ai_discussions.py`
- rank the top sessions worth reading
- return 2-5 session paths plus a short reason for each

Tell the subagent to:

- use the extractor script before opening raw JSONL files
- ignore `progress`, tool-use, tool-result, and file-history noise by default
- return concise findings, not a transcript dump
- include exact session file paths so the main agent can open the best candidates

Keep the final synthesis in the main agent. Use the subagent for discovery and triage, not for the final recap unless the task is explicitly parallelized by theme.

## Quick Start

If the user is asking for "recent discussions", "what did we conclude recently", "what project principles were settled", or similar, start with:

```bash
python3 ~/.codex/skills/ai-discussion-recap/scripts/extract_ai_discussions.py \
  --project /home/yu/projects/HaL \
  --days 14 \
  --max-sessions 8
```

If you need structured output for further filtering or your own analysis, add `--json`.
Use `--source claude`, `--source codex`, `--source pi`, or `--source windsurf` when you only want one store.

For very noisy sessions or pasted logs, prefer the extractor output first because it collapses long text and keeps the most useful edges of the conversation.

## Selection Rules

Treat these as high-signal and worth summarizing:

- User prompts that discuss architecture, principles, plans, refactors, tradeoffs, design direction, or major fixes.
- Assistant responses that contain explicit judgments, proposed structure, phased plans, constraints, or conclusions.
- Sessions where the first user message is substantive rather than a tiny follow-up like `continue`, `ok`, or `run tests`.
- Long pasted inputs only when they frame a design question, decision, or debugging direction.
- Codex or Pi sessions whose `cwd` matches the current project, or Windsurf (Devin Local) sessions whose `working_directory` matches, and contain real `user` and `assistant` messages after injected setup or runtime records.

Treat these as low-signal unless the user explicitly asks for them:

- `progress` events
- tool call payloads and tool results
- file-history snapshots
- short operational turns with no durable decision

## Raw JSONL Rules

The script already filters aggressively, but if you inspect raw JSONL yourself, focus on:

- `type == "user"` with real message text
- `type == "assistant"` text blocks only
- `type == "user_message"` or `payload.content` only when they contain real conversational text
- in Codex rollout files, `response_item` entries whose payload is `message` and role is `user` or `assistant`
- in Pi JSONL files, `type == "message"` records whose nested `message.role` is `user` or `assistant`, keeping only text blocks

Ignore tool-use blocks, tool results, event noise, Codex injected `developer` setup messages, and Pi runtime records like `model_change`, `thinking_level_change`, `custom`, plus `thinking` and `toolCall` blocks unless they directly explain a decision.

Read [references/jsonl-rules.md](references/jsonl-rules.md) only if you need the exact extraction heuristics or session-selection guidance.

When a user turn contains a very long pasted block, preserve the beginning and the end, omit the middle, and summarize what the pasted material is being used for.

## Output Shape

Prefer a compact recap in this form:

```markdown
## What We Decided
- ...

## Why
- ...

## Open Questions
- ...

## Next Steps
- ...
```

If the user asks for a timeline, organize by session date first and then summarize each session in 2-5 bullets.
