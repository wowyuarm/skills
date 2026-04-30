---
name: openclaw
description: Query OpenClaw documentation, implementation, and configuration. Use when asked about OpenClaw agent runtime, gateway, system prompt, tools, context engine, security, sandboxing, multi-agent routing, channels, plugins, skills, ACP, thinking/verbose/reasoning directives, or troubleshooting OpenClaw deployments. Triggers include: "openclaw", "agent-core", "pi-agent-core", "gateway config", "context engine", "system prompt assembly", "tool policy", "sandboxing", "compaction".
---

# OpenClaw

Answer OpenClaw questions fast using three primary sources, plus fallbacks.

## Source priority

| Priority | Source | For what |
|----------|--------|----------|
| 1 | Local docs (`openclaw/docs/`) | Config schema, concepts, CLI flags, user-facing features |
| 2 | DeepWiki (`openclaw/openclaw`) | Implementation details, source-level answers, architecture internals |
| 3 | Official website (`docs.openclaw.ai`) | Latest docs, reference, llms.txt index |

Fallback: web search, local dist code grep.

## 1. Local docs

Installed at: `/home/yu/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw/docs/`

Key directories (relative to docs root):

```
concepts/          agent-runtimes, agent-loop, system-prompt, context-engine
gateway/           config-agents, configuration, sandboxing, security/index
tools/             thinking, elevated
providers/         openai, anthropic, gemini, ...
plugins/           plugin architecture, SDK
security/          audit, model, trust boundaries
help/              faq
cli/               openclaw CLI reference
reference/         prompt-caching, ...
automation/        cron, heartbeats
channels/          telegram, discord, ...
pi.md              pi-agent-core integration
pi-dev.md          pi development
```

Quick lookups:

```
# Config reference
docs/gateway/config-agents.md

# Verbose / thinking / reasoning directives
docs/tools/thinking.md

# System prompt assembly
docs/concepts/system-prompt.md

# Context engine & compaction
docs/concepts/context-engine.md

# Agent execution loop
docs/concepts/agent-loop.md

# Tool policies
docs/tools/ (plus grep for "deny" in gateway/)

# Sandboxing
docs/gateway/sandboxing.md

# Security
docs/gateway/security/index.md

# Pi integration
docs/pi.md
docs/pi-dev.md

# FAQ
docs/help/faq.md
```

Search across all docs:
```bash
grep -rI --include="*.md" "keyword" ~/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw/docs/
```

## 2. DeepWiki

Uses `/home/yu/projects/yu-skills/deepwiki/scripts/deepwiki.sh` (fixed: proxy-first, then direct fallback).

```bash
deepwiki.sh s openclaw/openclaw       # list all topics
deepwiki.sh a openclaw/openclaw "..."  # ask a question
deepwiki.sh c openclaw/openclaw        # full contents (large)
```

Aliases: `s`, `a`, `c` for structure/ask/contents.

Good for: "how does X work internally", "where is Y implemented", "what files handle Z".

## 3. Official website

Base: `https://docs.openclaw.ai/`

Index: `https://docs.openclaw.ai/llms.txt` (all pages, agent-oriented)

Fetch with `web_fetch`, max 50000 chars per page.

Good for: latest docs that may not yet be in local install, cross-referencing, getting the full page when local docs feel incomplete.

## 4. Dist code

Installed at: `/home/yu/.nvm/versions/node/v24.13.1/lib/node_modules/openclaw/dist/`

Minified but grepable. Use sparingly — DeepWiki usually better for implementation questions.

Key bundles:
```
dist/agents/pi-embedded-runner/   # pi-agent-core integration
dist/agents/pi-bundle-*.js         # runtime, MCP materialise
```

## 5. Local CLI

```bash
openclaw --version
openclaw doctor
openclaw models status --probe
openclaw security audit --deep
openclaw config get
```

## 6. User config

```bash
~/.openclaw/openclaw.json5
```

Read this when the question is about the user's specific deployment, channel settings, agent profiles, or model allowlists.

## Common query patterns

| Question type | Go here first |
|---------------|---------------|
| What does config key X do? | Local docs → `grep` gateway/config-agents.md |
| How does thinking/verbose work? | Local docs → tools/thinking.md |
| How is system prompt built? | DeepWiki ask → Local docs concepts/system-prompt.md |
| How does compaction decide what to keep? | DeepWiki ask |
| What's the agent loop flow? | Local docs concepts/agent-loop.md + concepts/agent-runtimes.md |
| How does pi-agent-core get embedded? | DeepWiki ask + dist/agents/pi-embedded-runner/ |
| What tool policies can I set per channel? | Local docs → grep gateway/ for "tools.deny", "tools.profile" |
| How does sandboxing work? | Local docs → gateway/sandboxing.md |
| What's ACP and how to set it up? | Local docs concepts/ (search "acp") + pi-dev.md |
| User's current deployment state | Read ~/.openclaw/openclaw.json5 + openclaw doctor |
| Plugin/Skill development | Local docs plugins/ + pi-dev.md |
