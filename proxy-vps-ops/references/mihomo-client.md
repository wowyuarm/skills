# Mihomo / Clash Verge Rev Client

## Default client stance

Prefer a maintained Mihomo-based client such as **Clash Verge Rev**.

Do not design the default path around abandoned clients if the user is free to choose.

## Manual node workflow

For a self-hosted node, manual local config is often clearer than a remote subscription during the first pass.

Typical minimum config pieces:
- one proxy entry
- one proxy group
- a simple catch-all rule such as `MATCH,PROXY`

## VLESS + REALITY field mapping

Typical Mihomo proxy fields:
- `type: vless`
- `server: <public-ip-or-tailnet-ip>`
- `port: 443`
- `uuid: <uuid>`
- `network: tcp`
- `tls: true`
- `udp: true`
- `flow: xtls-rprx-vision`
- `servername: <same host used for REALITY>`
- `client-fingerprint: chrome`
- `reality-opts.public-key: <public-key>`
- `reality-opts.short-id: <short-id>`

Use the bundled template:
- [`../assets/mihomo-proxy.template.yaml`](../assets/mihomo-proxy.template.yaml)

## Public vs tailnet addressing

Default:
- use the VPS public IP for the proxy node
- use the tailnet IP for management

Only use the tailnet IP in the client config if the user explicitly wants a tailnet-only proxy.

## DNS and TUN caution

Once the node itself is proven good, client-side issues often come from:
- DNS settings
- TUN mode behavior
- system proxy conflicts
- rules that do not actually select the intended proxy group

When debugging, separate:
1. node reachability
2. handshake correctness
3. client routing behavior

## Common client-side mistakes

- wrong `servername`
- wrong public key or short ID
- forgetting `flow: xtls-rprx-vision`
- editing the proxy but not selecting the matching proxy group
- assuming `delay test failed` always means the server is down
- debugging TUN or DNS before proving raw TCP reachability to the node

## Minimal-first client guidance

For the first pass:
- use one node
- use one select group
- use a simple match rule
- verify raw connectivity before adding complex rulesets

Increase complexity only after the base path works.
