# AI Session Log Rules

## Relevant directories / data stores

Claude Code project histories are typically stored under:

- `~/.claude/projects/<project-slug>/**/*.jsonl`

Newer Claude Code releases sometimes nest sessions as `~/.claude/projects/<project-slug>/<session-uuid>/<root>.jsonl` with subagent transcripts under `<session-uuid>/subagents/agent-*.jsonl`. Both shapes should be picked up.

Codex rollout histories are typically stored under:

- `~/.codex/sessions/YYYY/MM/**/rollout-*.jsonl`

Pi histories are typically stored under:

- `~/.pi/agent/sessions/<project-slug>/*.jsonl`

A Claude project slug usually matches the absolute project path with `/` replaced by `-`.
Example: `/home/<user>/projects/<repo>` -> `-home-<user>-projects-<repo>`

When the slug directory is missing or yields fewer recent sessions than requested, fall back to scanning every `*.jsonl` under `~/.claude/projects/` and matching the first record's `cwd` field against the target project path (bounded to 200 candidates). The first record also exposes `gitBranch` and `model`, which are surfaced in the recap.

A Pi project slug usually strips leading/trailing `/`, replaces `/` with `-`, then wraps the result in `--`.
Example: `/home/<user>/projects/<repo>` -> `--home-<user>-projects-<repo>--`

## High-signal records

Prioritize these records when reconstructing a discussion:

- top-level `type: "user"` with real conversational text (skip records whose text starts with `<local-command-caveat>`, `<local-command-stdout>`, `<local-command-stderr>`, `<command-name>`, `<command-message>`, `<command-args>`, or `<system-reminder>`)
- top-level `type: "assistant"`
- event records with `type: "user_message"` and a useful `payload.content`
- in Codex rollout files, `response_item` records whose payload is `message` and role is `user` or `assistant`, after dropping any message whose combined text starts with one of the configured Codex noise prefixes (`# AGENTS.md instructions for `, `<environment_context>`, `<turn_aborted>`, `## Reasoning`, `Let me think about`)
- in Pi session files, `type: "message"` records whose nested `message.role` is `user` or `assistant`, with text read from `content` blocks of `type: "text"`. Consecutive identical turns (same role and same first ~200 characters) are deduped before scoring.

## What to ignore by default

Ignore these unless the user explicitly wants execution details:

- `type: "progress"`
- `type: "tool_call"`
- `tool_result` blocks inside message content
- `tool_use` blocks inside assistant content
- `type: "file-history-snapshot"`
- `type: "system"` command bookkeeping
- Claude user records that start with one of the system-injected prefixes above, since they are local-command echoes rather than real user turns
- Codex `response_item` records with role `developer`
- Codex `function_call`, `function_call_output`, `custom_tool_call`, `custom_tool_call_output`, and `reasoning` records unless the user explicitly wants execution details
- Pi runtime records such as `session`, `model_change`, `thinking_level_change`, and `custom`
- Pi nested `message.role: "toolResult"`
- Pi nested content blocks such as `thinking` and `toolCall` unless the user explicitly wants execution details

## Session ranking heuristics

Per store, at most `--per-source` candidate files (most recently modified first) are parsed at all; everything below applies after that cap.

Rank recent sessions higher when they contain one or more of these cues in the first user turn or repeated discussion text:

- `principle`, `design`, `architecture`, `refactor`, `plan`, `worker`, `memory`, `brief`, `thread`, `session`
- long-form explanation instead of single-word confirmation
- explicit tradeoff language such as `because`, `instead`, `should`, `must`, `not`, `prefer`

Downgrade sessions dominated by:

- tiny acknowledgements
- pure implementation logs
- repeated retries after a tooling problem
- Codex sessions whose visible content is mostly injected setup rather than actual user collaboration
- Pi sessions whose visible content is mostly provider/runtime switching, ping/pong checks, or tool output

## Summarization guidance

When producing the final recap:

- separate user requests from assistant conclusions
- preserve decisions and their reasons, not every turn
- mention exact dates when the user says "recent" if multiple days are involved
- prefer synthesis over transcript dumping
