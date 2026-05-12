---
name: openclaw-weixin-maintenance
description: "Maintain Yu's self-use OpenClaw Weixin plugin patch layer. Use when asked to update, rebase, merge PRs, inspect npm/GitHub drift, restore local patches after official updates, manage patch branches, or deploy the maintained openclaw-weixin plugin into ~/.openclaw/extensions/openclaw-weixin."
---

# OpenClaw Weixin Maintenance

Maintain a small local patch layer on top of official `@tencent-weixin/openclaw-weixin` npm packages.

## Repos and paths

- Maintenance repo: `/home/yu/projects/openclaw-weixin-maintained`
- PR/upstream work repo: `/home/yu/projects/openclaw-weixin`
- Live installed plugin: `/home/yu/.openclaw/extensions/openclaw-weixin`
- Live config: `/home/yu/.openclaw/openclaw.json`
- Patch backup dir: `/home/yu/.openclaw/patches`

## Branch model

In `/home/yu/projects/openclaw-weixin-maintained`:

- `vendor/npm-X.Y.Z`: exact official npm package import.
- `yu/base/npm-X.Y.Z-dev`: vendor branch plus local maintenance scaffolding such as `tsconfig.json`.
- `yu/patch/*`: one topic branch per patch.
- `yu/current`: integration branch; merge patch branches with `--no-ff` so included patches are visible.

Current important patch branches:

- `yu/patch/nonblocking-monitor`
- `yu/patch/configurable-block-streaming`
- `yu/patch/sender-id`
- `yu/patch/media-dedup`
- `yu/patch/gateway-methods`
- `yu/patch/voice-ref-msg`
- `yu/patch/log-dedupe`
- `yu/patch/suppress-cron-tool-warnings`

## OpenClaw 2026.5.x deploy-level patches (in `yu/current` dist/, not separate branches)

These are not upstream PRs but compatibility workarounds. They're applied directly
in `yu/current`'s source files and survive `tsc` rebuilds:

- `src/runtime.ts`: store PluginRuntime on `globalThis.__weixinPluginRuntime` because
  OpenClaw 2026.5.x re-initializes ESM module state between `register()` and channel
  startup, resetting module-level `let` variables to `null`.
- `src/api/api.ts`: removed manual `Content-Length` header from `buildHeaders()` because
  OpenClaw's bundled undici 8.x rejects it with `UND_ERR_INVALID_ARG`.
- `MAINTAINING.md` has full deploy gotchas.

## Mandatory workflow

1. Check current state.

```bash
cd /home/yu/projects/openclaw-weixin-maintained
git status --short --branch
git branch --list 'vendor/*' 'yu/*'
cat MAINTAINING.md
```

2. Before changing anything, identify official source:

```bash
npm view @tencent-weixin/openclaw-weixin version time.modified dist-tags.latest --json
```

If user asks about GitHub drift, also check:

```bash
git ls-remote --tags https://github.com/Tencent/openclaw-weixin.git
git ls-remote https://github.com/Tencent/openclaw-weixin.git HEAD
```

3. Keep `vendor/npm-*` branches exact. Do not edit them after import.

4. Put every local change in a `yu/patch/*` branch first. Then merge it into `yu/current` with `--no-ff`.

5. When official npm updates:

- import new package into `vendor/npm-X.Y.Z`
- create `yu/base/npm-X.Y.Z-dev`
- replay only still-needed patch branches
- drop patches already fixed upstream
- rebuild `yu/current`

6. Verify before reporting or deploying:

```bash
npm install --ignore-scripts
npm run typecheck
npm run build
```

If tests are present in the active branch, run targeted tests too. If no tests are present because branch is based on npm package source, say that plainly.

## Deployment rule

Do not overwrite live plugin until `yu/current` passes checks.

When deploying, preserve OpenClaw account/config state under `~/.openclaw`; only replace plugin source directory contents. Then validate config and restart gateway.

Suggested checks after deploy:

```bash
openclaw config validate
openclaw channels status --json
```

If gateway is restarted manually, capture log path and PID.

## PR triage rules

Prefer small, reversible fixes:

- Good: inbound poll nonblocking, configurable block streaming, SenderId, media dedup, gateway method metadata, voice quote context, noisy log reduction.
- Risky: large ACP thread-binding changes, broad chunking behavior changes, voice-send PRs with lockfile or whole-repo patch shape.

For each PR, inspect files and decide:

```bash
curl -fsSL https://github.com/Tencent/openclaw-weixin/pull/NUMBER.patch -o /tmp/pr-NUMBER.patch
git apply --check --exclude='*.test.ts' /tmp/pr-NUMBER.patch
```

If patch does not apply over npm branch, port manually and keep commit message referencing original PR number.

## Reporting style

Tell user:

- official version used
- patch branches included
- checks run and results
- whether live plugin was changed
- what remains risky or unverified
