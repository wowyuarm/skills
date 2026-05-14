---
name: deepwiki
description: >-
  Query DeepWiki documentation for any public GitHub repository directly via HTTP,
  without needing an MCP connection. Use when the agent needs to look up
  documentation, browse wiki structure, or ask questions about a GitHub
  repository's architecture and code. Triggers include: "deepwiki", "look up
  repo docs", "what does this repo do", "ask deepwiki", and "how does this
  repo work".
---

# DeepWiki

Query the [DeepWiki](https://deepwiki.com) API via JSON-RPC over HTTP.
No MCP client needed — just a single Python script with stdlib.

## Architecture

```
scripts/
├── deepwiki      # Python CLI (stdlib only: json, urllib)
└── deepwiki.sh   # Bash wrapper → delegates to deepwiki
```

The heavy lifting (JSON-RPC construction, SSE parsing, proxy fallback, error handling)
is all in `deepwiki`. The shell wrapper just resolves the script directory and `exec`s
into Python — no inline JSON escaping, no sed/pipe chains.

## Commands

```bash
# List documentation topics for a repo
scripts/deepwiki.sh structure <owner/repo>

# View full documentation
scripts/deepwiki.sh contents <owner/repo>

# Ask a question about a repo
scripts/deepwiki.sh ask <owner/repo> "question"
```

Aliases: `s` `c` `a`. `scripts/deepwiki` also works directly.

## When to Use

- Understand an unfamiliar repository's architecture before working with it
- Look up how a specific feature or subsystem is implemented
- Get a structured overview (table of contents) of a repo's documentation
- Answer questions about a codebase without cloning or reading source directly

## Notes

- Free, no authentication required. Public GitHub repositories only.
- The `DEEPWIKI_ENDPOINT` env var can override the default API URL.
