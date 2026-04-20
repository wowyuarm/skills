---
name: proxy-vps-ops
description: Plan, bootstrap, operate, verify, troubleshoot, optimize, migrate, and rebuild a self-hosted VPS used as a personal proxy node. Use when working on VPS region or billing choices, Ubuntu baseline setup, Tailscale management access, Xray-core with VLESS + REALITY deployment, Mihomo/Clash client configuration, optional Surge + Snell + ShadowTLS alternative deployments when explicitly requested, listener or firewall debugging, day-2 maintenance, performance tuning, or node replacement and recovery.
---

# Proxy VPS Ops

Manage the full lifecycle of a self-hosted VPS used as a personal proxy node.

Treat deployment as only one phase. Cover planning, bootstrap, management-plane access, proxy-plane deployment, verification, hardening, operations, troubleshooting, optimization, migration, and rebuild.

## Mandatory state protocol

Always start by checking for [`references/current-state.local.md`](references/current-state.local.md).

If it exists:
- read it first
- treat it as the active engagement ledger

If it does not exist:
- read [`references/current-state.template.md`](references/current-state.template.md)
- create `references/current-state.local.md` from that template
- fill in the known facts for the current engagement before continuing

Treat the local state file as the active engagement ledger:
- Use it to learn what is already known, what was already changed, and what still needs verification.
- Do not re-collect facts that are already present and still credible unless the user asks for re-validation or the file looks stale, contradictory, or belongs to a different node.
- If the current request is clearly about a different VPS, client, or goal, rewrite `references/current-state.local.md` for the new engagement before continuing.
- After every meaningful milestone, update `references/current-state.local.md` with verified facts, recent changes, open questions, current phase, and next actions.
- Never invent facts in the state file. Mark uncertain items explicitly as reported, unverified, stale, or guessed.

`current-state.template.md` is stable guidance and should stay shareable. `current-state.local.md` is runtime state and is expected to change during normal use. Treat the other reference files as stable guidance unless the user explicitly asks to improve the skill itself.

## Operating model

Work in this order:
1. Read the current state file.
2. Determine where you are operating from: local machine, VPS shell, or guided-commands mode.
3. Classify the request.
4. Load only the relevant reference files.
5. Make the smallest correct change.
6. Verify at the right layer.
7. Update the state file.

## First questions to settle

Resolve these early if the state file does not already answer them:
- What is the target VPS and what is the management path to it?
- Is the goal planning, bootstrap, deploy, verify, debug, optimize, or migrate?
- Is the proxy expected to be publicly reachable, tailnet-only, or both?
- What client is in use locally?
- Is the user validating a new provider/region or maintaining an existing node?

## Default opinionated path

Use this default unless the user asks for a different stack or the environment clearly requires one:
- Ubuntu LTS on the VPS
- Tailscale for the management plane
- Xray-core with VLESS + REALITY for the proxy plane
- Mihomo / Clash Verge Rev on the client
- UFW for simple firewall management
- Minimal first iteration: no panel, no reverse proxy, no CDN, no domain, no extra protocols

Alternative branch, only when user explicitly wants it:
- Surge-focused client path with Snell, optionally wrapped by ShadowTLS
- Keep this as opt-in, not default

If the user mainly wants to validate provider quality before committing to the full proxy stack, it is acceptable to suggest a simpler baseline such as WireGuard for line testing. Still keep management and proxy roles conceptually separate.

## Request classification

### 1. Plan
Read:
- [`references/scope-and-architecture.md`](references/scope-and-architecture.md)
- [`references/provider-and-sizing.md`](references/provider-and-sizing.md)

Use for:
- provider or region choice
- bandwidth vs traffic billing
- shared vs dedicated CPU
- deciding whether the node should be public or tailnet-only

### 2. Bootstrap
Read:
- [`references/bootstrap-ubuntu.md`](references/bootstrap-ubuntu.md)
- [`references/management-plane-tailscale.md`](references/management-plane-tailscale.md)

Use for:
- first login
- package updates
- SSH, firewall, hostname, and console recovery basics
- Tailscale installation and management-path setup

### 3. Deploy
Read:
- [`references/proxy-plane-xray-reality.md`](references/proxy-plane-xray-reality.md)
- [`references/mihomo-client.md`](references/mihomo-client.md)
- [`references/alternative-stack-snell-shadowtls.md`](references/alternative-stack-snell-shadowtls.md) when the user asks for Surge, Snell, or ShadowTLS

Use for:
- Xray install and config
- REALITY material generation
- service management
- Mihomo/Verge Rev node creation
- optional Snell + ShadowTLS deployment planning when explicitly requested

Use bundled helpers when useful:
- [`scripts/generate_reality_materials.sh`](scripts/generate_reality_materials.sh)
- [`assets/xray-config.template.json`](assets/xray-config.template.json)
- [`assets/mihomo-proxy.template.yaml`](assets/mihomo-proxy.template.yaml)

### 4. Verify
Read:
- [`references/verification-ladder.md`](references/verification-ladder.md)

Use for:
- proving the node works end-to-end
- identifying the exact failing layer before editing config

### 5. Debug
Read:
- [`references/verification-ladder.md`](references/verification-ladder.md)
- [`references/troubleshooting.md`](references/troubleshooting.md)

Use for:
- connection refused
- timeout
- service active but no listener
- handshake failure
- connected but no traffic
- partial connectivity

Prefer minimal changes and rank hypotheses. Avoid redesigning the stack before isolating the failing layer.

Use [`scripts/collect_xray_diagnostics.sh`](scripts/collect_xray_diagnostics.sh) when Xray service state, listener state, or systemd behavior is in question.

### 6. Operate / Harden
Read:
- [`references/operations.md`](references/operations.md)
- [`references/management-plane-tailscale.md`](references/management-plane-tailscale.md)

Use for:
- day-2 maintenance
- package or Xray updates
- firewall tightening
- SSH exposure reduction
- backups and change discipline

### 7. Optimize
Read:
- [`references/optimization.md`](references/optimization.md)
- [`references/provider-and-sizing.md`](references/provider-and-sizing.md)

Use for:
- speed complaints
- evening instability
- jitter and packet loss
- evaluating whether to tune or replace the node

### 8. Migrate / Rebuild
Read:
- [`references/migration-and-rebuild.md`](references/migration-and-rebuild.md)
- [`references/operations.md`](references/operations.md)

Use for:
- moving to a new VPS or IP
- recovering from a bad node
- recreating the node without losing track of required client and server values

## Core mental model

Keep these layers separate:
1. provider and route quality
2. VPS baseline health
3. management plane reachability
4. proxy service process state
5. listener state
6. local TCP reachability on the VPS
7. public TCP reachability from the client side
8. protocol handshake correctness
9. client routing, TUN, DNS, and policy behavior

Do not skip layers. "Service active" does not prove "listener exists". "Firewall open" does not prove "process is bound". "TCP connect works" does not prove "REALITY parameters match".

## Non-negotiable habits

- Prefer the smallest fix that explains the evidence.
- Verify before and after changes.
- Preserve management access before tightening exposure.
- Keep management plane and proxy plane conceptually separate.
- Prefer maintained clients and defaults over abandoned tools.
- Prefer inspectable manual steps over opaque one-click installers; borrow patterns, not black boxes.
- Treat provider quality as a first-class variable; do not over-credit protocol tweaks.
- Avoid exposing secrets in chat output unless the user explicitly needs the raw values.

## Completion protocol

Before finishing, update `references/current-state.local.md`.

At minimum refresh:
- active objective
- target systems and identities
- current phase
- verified facts
- recent changes
- open questions or risks
- next recommended actions
- last updated timestamp
