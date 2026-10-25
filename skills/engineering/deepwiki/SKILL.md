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
No MCP client needed — a single Python script using only the stdlib.

## Commands

```bash
# List documentation topics for a repo
scripts/deepwiki structure <owner/repo>

# View full documentation (large — redirect to a file)
scripts/deepwiki contents <owner/repo>

# Ask a question about a repo
scripts/deepwiki ask <owner/repo> "question"
```

Aliases: `s` `c` `a`.

## When to Use

- Understand an unfamiliar repository's architecture before working with it
- Look up how a specific feature or subsystem is implemented
- Get a structured overview (table of contents) of a repo's documentation
- Answer questions about a codebase without cloning or reading source directly

## Notes

- Free, no authentication required. Public GitHub repositories only.
- The `DEEPWIKI_ENDPOINT` env var can override the default API URL.
- Exit status is 0 only on success; any error prints to stderr and exits 1.
- A repo DeepWiki has not indexed fails with a "Visit https://deepwiki.com/… to
  index it" message — open that URL to request indexing, then retry.
- `contents` returns the full wiki (hundreds of KB even for small repos).
  Prefer `structure` plus targeted `ask`; redirect `contents` to a file.
