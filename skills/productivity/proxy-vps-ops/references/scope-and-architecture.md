# Scope And Architecture

## What this skill covers

Manage a VPS that exists primarily to serve as a personal proxy node.

Cover:
- provider and sizing decisions
- VPS baseline setup
- management-plane access
- proxy-plane deployment
- end-to-end verification
- hardening, operations, troubleshooting, optimization, migration, and rebuild

Do not drift into generic VPS administration unless it directly affects the proxy node.

## Core separation: management plane vs proxy plane

### Management plane
Use the management plane for:
- SSH
- file editing
- logs
- service control
- recovery access

Default choice: **Tailscale**.

### Proxy plane
Use the proxy plane for:
- client traffic from Mihomo / Clash Verge Rev
- public proxy reachability when the user wants normal Internet access through the node

Default choice: **Xray-core + VLESS + REALITY**.

Keep these planes conceptually separate even when they share the same VPS.

## Default deployment shape

For a typical first version:
- public IP exists on the VPS
- proxy port is publicly reachable
- SSH stays available until Tailscale is proven stable
- once Tailscale management is trusted, reduce public management exposure

## Tailnet-only mode

Use tailnet-only proxy access only if the user clearly wants that model and all client devices can reach the VPS over Tailscale.

This is more restrictive and usually not the simplest first path.

## Minimal-first principle

Prefer this order:
1. make the node reachable and understandable
2. verify end-to-end connectivity
3. tighten exposure and improve maintenance posture
4. tune or migrate only if evidence justifies it

Avoid piling on extra moving parts during the first pass:
- no panel by default
- no reverse proxy by default
- no domain or certificate stack unless required
- no multi-protocol setup unless the user specifically needs it

## Default opinionated stack

Use this stack unless the user asks otherwise:
- Ubuntu LTS
- UFW
- Tailscale for management
- Xray-core on the VPS
- VLESS + REALITY for the public proxy path
- Mihomo / Clash Verge Rev on the client

## Alternative stack branch: Surge + Snell (+ ShadowTLS)

Use this only when the user clearly wants a Surge-native path or is already committed to Snell.

Good fit when:
- user mainly uses Surge
- user wants Snell specifically
- Apple-centric client flow matters more than broad client compatibility

Not default when:
- user wants broad cross-client compatibility
- Mihomo / Clash path already works
- user does not need Snell-specific behavior

If this branch is chosen:
- keep Tailscale as management plane
- keep same layered verification model
- prefer Snell v4 as stable baseline
- use Snell v5 only when both ends support it and its extra features matter
- if ShadowTLS wraps Snell, prefer exposing ShadowTLS public port and keeping raw Snell upstream local-only when practical

## Primary mental model

When something breaks, reason by layers:
1. provider route quality
2. VPS baseline health
3. management reachability
4. service process state
5. listener state
6. local TCP reachability on the VPS
7. external TCP reachability
8. protocol handshake correctness
9. client routing, DNS, and TUN behavior

Do not start with the client if the server is not even listening.
