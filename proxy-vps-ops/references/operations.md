# Operations

## Day-2 mindset

A self-hosted proxy node is not done after first success.

Operate it like a small, single-purpose service:
- keep access paths clear
- keep changes small and reversible
- record decisions and current state
- verify after maintenance

## Change discipline

Before making changes:
- read `current-state.local.md` if it exists, otherwise initialize it from `current-state.template.md`
- confirm the current phase and objective
- preserve a recovery path
- prefer one change at a time

After making changes:
- verify at the right layer
- update `current-state.local.md`

## Routine checks

Use these periodically:

```bash
systemctl status xray --no-pager -l
journalctl -u xray --no-pager -n 100
ss -ltnp | grep ':443'
ufw status verbose
tailscale status
```

## Backup priorities

At minimum, know how to recover or reproduce:
- `/usr/local/etc/xray/config.json`
- systemd overrides related to Xray
- generated REALITY values and client mapping
- firewall posture
- tailnet identity and intended management path

Do not leave recovery dependent on memory alone.

## Update strategy

When updating packages or Xray/Tailscale:
1. capture the current state
2. update one layer at a time
3. re-check listener state
4. re-check local and external TCP reachability
5. note the result in the state file

## SSH exposure

Once Tailscale management is proven stable, decide deliberately whether public SSH should remain open.

Do not leave this ambiguous forever. Record the policy in the state file.

## Service posture

If a temporary workaround such as running as root was used to restore service, keep it working first and only redesign later with a clear verification plan.

## Signs the node needs attention

- the client starts timing out or getting refused connections
- evening performance worsens repeatedly
- logs show repeated startup, bind, or handshake issues
- Tailscale management is no longer reliable
- the provider route or IP reputation becomes the main complaint
