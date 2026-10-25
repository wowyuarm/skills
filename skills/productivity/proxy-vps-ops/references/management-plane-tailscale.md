# Management Plane: Tailscale

## Purpose

Use Tailscale to manage the VPS more safely and consistently.

Use it for:
- SSH and shell access
- log collection
- service management
- recovery from public-management mistakes

Do not automatically treat Tailscale as the public proxy data path.

## Default approach

1. install Tailscale
2. join the tailnet
3. verify the VPS gets a `100.x` address
4. verify client devices can reach that address
5. keep public SSH until this path is trusted
6. then tighten public management exposure if the user wants

## Installation pattern

Typical sequence:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
tailscale status
```

Record the assigned tailnet IP in the state file.

## Management rules

- Treat the tailnet IP as the preferred management address.
- Keep the public IP for the proxy plane unless the user explicitly wants a tailnet-only proxy.
- Make sure the local device that needs management access is also on Tailscale.

## Public SSH tightening

Only reduce public SSH exposure after all of these are true:
- tailnet access works from the user device
- the user is comfortable reconnecting over Tailscale
- a recovery path still exists through the provider console

Possible tightening steps:
- restrict or close public `22/tcp`
- keep only the proxy port public
- document the change in the state file

## Tailnet-only proxy mode

Use this only when the user explicitly wants the proxy accessible only from devices in the tailnet.

Implications:
- client devices must run Tailscale
- the client config must target the tailnet IP instead of the public IP
- this is more restrictive, not the default first path

## Common mistakes

- mixing up public IP and tailnet IP roles
- closing public SSH before testing tailnet access from the actual client device
- assuming Tailscale installation alone means management access is proven
- debugging public proxy failures through Tailscale-specific assumptions

## Verification

Check:

```bash
tailscale ip -4
tailscale status
ip -brief addr
```

From a client device, prove that the tailnet IP is reachable before relying on it.
