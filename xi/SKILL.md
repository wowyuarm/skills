---
name: xi
description: "Use whenever the user mentions Xi/曦, Xi runtime, Xi VPS, Xi daemon, consolidation, daily steward, message tool, wake loop, Xi memory pipeline, Xi weixin/channel, Xi deployment, or Xi system design. Covers codebase, architecture, workspace, VPS ops, systemd, deploy flow, testing isolation, OpenClaw legacy migration, and troubleshooting."
---

# Xi 曦 Runtime

Use this skill for all Xi/曦 work. Xi is now a standalone runtime built on Pi SDK full-control mode, not an OpenClaw plugin and not a Pi extension.

## Mandatory state protocol

Always start by reading [`references/current-state.local.md`](references/current-state.local.md).

If it does not exist:
1. read [`references/current-state.template.md`](references/current-state.template.md)
2. create `current-state.local.md` from the template
3. fill only verified facts; mark unknowns explicitly

Treat `current-state.local.md` as the active engagement ledger:
- Reuse verified deployment facts instead of rediscovering them.
- Update it after every meaningful milestone: deploy, service restart, VPS hardening, channel cutover, migration, incident, or design decision.
- Never store secrets, tokens, API keys, Tailscale auth keys, or private key contents.
- If local and VPS differ, inspect/diff before syncing. Never blindly overwrite production `~/.xi`.

## Source priority

| Priority | Source | For what |
| --- | --- | --- |
| 1 | `references/current-state.local.md` | Current VPS/service/workspace state |
| 2 | `/home/yu/projects/Xi/AGENTS.md` | Contributor rules and current repo conventions |
| 3 | `/home/yu/projects/Xi/ARCHITECTURE.md` | Runtime design and memory pipeline |
| 4 | `/home/yu/projects/Xi/README.md` | Commands and rewrite summary |
| 5 | Code under `/home/yu/projects/Xi/src/` | Exact behavior |
| 6 | `~/.xi/` | Local production workspace / history |
| 7 | `~/.openclaw/` | Archived OpenClaw legacy context |

## Critical operating rule: isolated tests first

Do **not** test runtime changes directly in production `XI_HOME` unless the user explicitly asks for a real wake/chat.

Use isolation for smoke tests:

```bash
XI_HOME=/tmp/xi-smoke PI_AGENT_DIR=/home/xi/.pi/agent node dist/cli.js status
```

Deployment scripts must build and smoke-test with `/tmp/xi-smoke` before restarting `xi-daemon`. Production daemon restart is a real event: it triggers a startup wake and writes to `/home/xi/.xi`.

## Local and VPS paths

Local:
- Code: `/home/yu/projects/Xi`
- Workspace: `/home/yu/.xi`
- Deploy helper: `/home/yu/bin/deploy-xi-vps`

VPS:
- Code: `/opt/xi/Xi`
- Workspace: `/home/xi/.xi`
- Pi agent dir: `/home/xi/.pi/agent`
- Env file: `/etc/xi/xi.env`
- Service: `xi-daemon.service`
- Deploy script: `/usr/local/bin/deploy-xi`

## Deployment model

Use systemd for the daemon. Use deploy scripts for updates.

Local fast path:

```bash
cd /home/yu/projects/Xi
npm run typecheck
/home/yu/bin/deploy-xi-vps --no-restart   # build + isolated smoke only
/home/yu/bin/deploy-xi-vps                # build + isolated smoke + production restart
```

Remote script behavior:
1. install dependencies
2. TypeScript build
3. create `/tmp/xi-smoke`
4. copy SOUL/INSTRUCTIONS/MEMORY only into smoke workspace
5. run `xi status` in smoke workspace
6. restart `xi-daemon` only if requested/default

## Architecture summary

- Xi herself is `createXiSession()`.
- Utility agents are organs: direction, daily-steward, consolidation, git-summarizer.
- `message` tool is the only outbound path to Yu; text/thinking are internal.
- Direction runs on wake only, not every chat.
- Daily steward writes segment narratives and `## candidates`.
- Consolidation runs after 03:00, reads candidates + evidence, promotes stable knowledge.
- Logical day boundary is 03:00 Asia/Shanghai.
- Quiet hours: 01:00–07:00, Xi can explore but defaults not to message.
- Context model: append-only `xi.jsonl` truth + rebuilt LLM context each turn.

## OpenClaw legacy rule

OpenClaw legacy data is archived context, not the active runtime. Use it for history only.

- Local backup: `~/.openclaw`
- Current Xi migrated daily memory: `~/.xi/daily/2026-04-29.md` through current day
- Do not import OpenClaw runtime state wholesale into Xi.
- If extracting legacy content, prefer library/archive or daily/consolidation paths, not direct state injection.

## VPS hardening rule

Before closing public SSH, verify Tailscale management works from Yu's machine.

Safe order:
1. bring up Tailscale
2. verify SSH over Tailscale
3. allow SSH on `tailscale0`
4. enable UFW
5. disable password SSH / optionally close public 22
6. verify root recovery path

## Completion protocol

Before reporting completion:
- run actual verification at the right layer
- check `systemctl status xi-daemon` if service touched
- inspect `events/<day>.jsonl` if daemon/wake touched production
- update `references/current-state.local.md`
- consider Nowledge Mem only after skill/current-state and docs are current
