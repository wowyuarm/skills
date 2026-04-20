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

Simple timestamped backup pattern:

```bash
backup_dir=/root/proxy-backups/$(date +%Y%m%d-%H%M%S)
mkdir -p "$backup_dir"
cp -a /usr/local/etc/xray/config.json "$backup_dir"/
systemctl cat xray > "$backup_dir"/xray.unit.txt
ufw status numbered > "$backup_dir"/ufw-status.txt
```

Do not leave recovery dependent on memory alone.

## Update strategy

When updating packages or Xray/Tailscale:
1. capture the current state
2. update one layer at a time
3. re-check listener state
4. re-check local and external TCP reachability
5. note the result in the state file

## Long-running apt over SSH

On slow provider links (observed: LightNode SG egress ~120 KB/s, `linux-firmware` alone ~316 MB), a naive `ssh root@host 'apt-get dist-upgrade'` pattern is fragile. If the SSH client hits a timeout or disconnects, the reader at the end of the remote shell pipeline can die and `apt-get` either stalls or is killed by SIGPIPE mid-run, leaving the system in a partially-upgraded state.

For any multi-minute apt or dpkg operation started remotely, detach it from the SSH session:

```bash
systemd-run --unit=apt-dist-upgrade \
  --description="apt dist-upgrade" \
  --property=StandardOutput=file:/tmp/apt-upgrade.log \
  --property=StandardError=file:/tmp/apt-upgrade.log \
  /bin/bash -c 'DEBIAN_FRONTEND=noninteractive apt-get -y \
    -o Dpkg::Options::=--force-confold \
    -o Dpkg::Options::=--force-confdef \
    -o Acquire::Retries=3 \
    dist-upgrade'
```

Then poll `systemctl is-active apt-dist-upgrade` and tail `/tmp/apt-upgrade.log`. The run survives your SSH session ending and keeps a complete log on disk.

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
