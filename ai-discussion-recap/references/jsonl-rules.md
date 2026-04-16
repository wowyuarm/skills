# AI Session Log Rules

## Relevant directories

Claude Code project histories are typically stored under:

- `~/.claude/projects/<project-slug>/*.jsonl`

Codex rollout histories are typically stored under:

- `~/.codex/sessions/YYYY/MM/**/rollout-*.jsonl`

A project slug usually matches the absolute project path with `/` replaced by `-`.
Example: `/home/yu/projects/HaL` -> `-home-yu-projects-HaL`

## High-signal records

Prioritize these records when reconstructing a discussion:

- top-level `type: "user"`
- top-level `type: "assistant"`
- event records with `type: "user_message"` and a useful `payload.content`
- in Codex rollout files, `response_item` records whose payload is `message` and role is `user` or `assistant`

## What to ignore by default

Ignore these unless the user explicitly wants execution details:

- `type: "progress"`
- `type: "tool_call"`
- `tool_result` blocks inside message content
- `tool_use` blocks inside assistant content
- `type: "file-history-snapshot"`
- `type: "system"` command bookkeeping
- Codex `response_item` records with role `developer`
- Codex `function_call`, `function_call_output`, `custom_tool_call`, `custom_tool_call_output`, and `reasoning` records unless the user explicitly wants execution details

## Session ranking heuristics

Rank recent sessions higher when they contain one or more of these cues in the first user turn or repeated discussion text:

- `principle`, `design`, `architecture`, `refactor`, `plan`, `worker`, `memory`, `brief`, `thread`, `session`
- long-form explanation instead of single-word confirmation
- explicit tradeoff language such as `because`, `instead`, `should`, `must`, `not`, `prefer`

Downgrade sessions dominated by:

- tiny acknowledgements
- pure implementation logs
- repeated retries after a tooling problem
- Codex sessions whose visible content is mostly injected setup rather than actual user collaboration

## Summarization guidance

When producing the final recap:

- separate user requests from assistant conclusions
- preserve decisions and their reasons, not every turn
- mention exact dates when the user says "recent" if multiple days are involved
- prefer synthesis over transcript dumping
