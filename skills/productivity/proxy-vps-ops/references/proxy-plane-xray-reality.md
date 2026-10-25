# Proxy Plane: Xray + VLESS + REALITY

## Default choice

Use **Xray-core** as the default server for the public proxy plane.

Reasoning:
- mature fit for VLESS + REALITY
- works well with Mihomo / Clash Verge Rev clients
- avoids extra domain and certificate setup for the first version

## Minimal deployment path

1. install Xray-core from the official installer
2. generate UUID, x25519 key pair, and short ID
3. write a minimal VLESS + REALITY config
4. validate the config
5. start the service
6. prove that the listener exists
7. generate the client config
8. verify end-to-end

## Generate REALITY materials

Typical commands:

```bash
/usr/local/bin/xray uuid
/usr/local/bin/xray x25519
openssl rand -hex 8
```

Or use the bundled helper:

```bash
./scripts/generate_reality_materials.sh
```

Use the outputs for:
- UUID
- private key
- public key
- short ID

## Config skeleton

Use the bundled template as a starting point:
- [`../assets/xray-config.template.json`](../assets/xray-config.template.json)

Typical defaults for the first pass:
- `listen: 0.0.0.0`
- `port: 443`
- `protocol: vless`
- `flow: xtls-rprx-vision`
- `network: tcp`
- `security: reality`

## REALITY destination choice

Choose a destination that is:
- public
- TLS-enabled
- stable
- supportive of TLS 1.3 / HTTP/2 in practice

Use the same host consistently in server-side `dest`, `serverNames`, and the client's `servername`.

## Service management rules

Always validate config syntax first:

```bash
/usr/local/bin/xray run -test -config /usr/local/etc/xray/config.json
```

Then manage the service with systemd.

## Critical warning: active service is not enough

Do not stop at `systemctl status xray`.

Also verify:

```bash
ss -ltnp | grep ':443'
timeout 3 bash -lc '</dev/tcp/127.0.0.1/443' && echo OPEN || echo CLOSED
```

A service can be `active` while failing to create the listener.

## Privileged port caution

When binding `:443`, remember it is a privileged port.

If the process is active but not listening, check:
- runtime user
- capabilities
- systemd sandboxing or overrides
- foreground manual execution versus systemd execution

Useful isolation steps:
1. compare systemd execution with foreground manual execution
2. if needed, temporarily test a non-privileged port such as `8443`
3. if that changes behavior, focus on service user and bind permissions before blaming REALITY

## Install-order gotcha: restart after writing the override

The official `XTLS/Xray-install` script does `systemctl enable --now xray` as part of install. If you then write a drop-in like `/etc/systemd/system/xray.service.d/20-local-root.conf` with `User=root`, a subsequent `systemctl enable --now xray` is a no-op because the unit is already enabled and running. The old `nobody` process keeps running, `systemctl show xray -p User` reports `root`, and you get a very confusing split state where the effective user disagrees with the actual process user.

Always run `systemctl restart xray` after writing or changing the override, not just `daemon-reload` + `enable --now`. Verify with `ps -o pid,user,cmd -p $(pgrep -f 'xray run')` and `ss -tlnp | grep ':443 '` immediately after.

## Listener-first troubleshooting principle

For `connection refused`, prove or disprove listener creation before touching client config.

Good order:
1. config test
2. `systemctl cat xray`
3. `ss -ltnp`
4. local TCP connect
5. external TCP connect
6. only then client handshake fields

## Useful diagnostics

Use the bundled collector when debugging Xray service state:

```bash
./scripts/collect_xray_diagnostics.sh
```

## Client field mapping

Server-side values map to client values roughly like this:
- UUID -> `uuid`
- public key -> `reality-opts.public-key`
- short ID -> `reality-opts.short-id`
- server name -> `servername`
- `flow: xtls-rprx-vision` -> client `flow`

Use the bundled client template:
- [`../assets/mihomo-proxy.template.yaml`](../assets/mihomo-proxy.template.yaml)
