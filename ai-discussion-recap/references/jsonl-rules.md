# AI Session Log Rules

## Relevant directories / data stores

Claude Code project histories are typically stored under:

- `~/.claude/projects/<project-slug>/*.jsonl`

Codex rollout histories are typically stored under:

- `~/.codex/sessions/YYYY/MM/**/rollout-*.jsonl`

Pi histories are typically stored under:

- `~/.pi/agent/sessions/<project-slug>/*.jsonl`

Windsurf (Devin Local) conversation history is stored in an SQLite database:

- `~/.local/share/devin/cli/sessions.db`

  - `sessions` table: `id`, `working_directory` (backslash-separated on all platforms),
    `model`, `title`, `created_at`, `last_activity_at` (Unix timestamps)
  - `message_nodes` table: `session_id`, `node_id`, `parent_node_id`,
    `chat_message` (JSON with `role`, `content`, `message_id`,
    optional `tool_calls` and `thinking`), `created_at` (Unix timestamp)
  - The `message_nodes` table is a tree: the same `message_id` can appear at
    multiple `node_id` values. Deduplicate by `message_id` on first encounter.
  - Skip `role: system` and `role: tool` records. Extract only `user`
    and `assistant` with non-empty `content` text.

A Claude project slug usually matches the absolute project path with `/` replaced by `-`.
Example: `/home/yu/projects/HaL` -> `-home-yu-projects-HaL`

A Pi project slug usually strips leading/trailing `/`, replaces `/` with `-`, then wraps the result in `--`.
Example: `/home/yu/projects/HaL` -> `--home-yu-projects-HaL--`

## High-signal records

Prioritize these records when reconstructing a discussion:

- top-level `type: "user"`
- top-level `type: "assistant"`
- event records with `type: "user_message"` and a useful `payload.content`
- in Codex rollout files, `response_item` records whose payload is `message` and role is `user` or `assistant`
- in Pi session files, `type: "message"` records whose nested `message.role` is `user` or `assistant`, with text read from `content` blocks of `type: "text"`
- in Windsurf (Devin Local) SQLite DB, `message_nodes` rows whose `chat_message` JSON has `role: "user"` or `role: "assistant"` with non-empty `content` string

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
- Pi runtime records such as `session`, `model_change`, `thinking_level_change`, and `custom`
- Pi nested `message.role: "toolResult"`
- Pi nested content blocks such as `thinking` and `toolCall` unless the user explicitly wants execution details

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
- Pi sessions whose visible content is mostly provider/runtime switching, ping/pong checks, or tool output

## Summarization guidance

When producing the final recap:

- separate user requests from assistant conclusions
- preserve decisions and their reasons, not every turn
- mention exact dates when the user says "recent" if multiple days are involved
- prefer synthesis over transcript dumping
