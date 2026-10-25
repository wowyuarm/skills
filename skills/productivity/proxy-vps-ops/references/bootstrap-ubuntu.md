# Bootstrap Ubuntu

## Goal

Turn a fresh VPS into a safe, understandable machine before deploying the proxy stack.

## Baseline sequence

1. confirm console or SSH access
2. identify the default login model
3. update packages
4. ensure a recovery path exists
5. open only the ports currently needed
6. fix basic hostname issues
7. record the state

## First access

Prefer this order:
- try provider console or VNC if SSH credentials are unclear
- confirm the default user model: `root`, cloud user, or injected SSH key
- only create additional users after basic access is stable

## Package baseline

Typical first commands:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y curl ufw unzip uuid-runtime ca-certificates
```

Install extra editors or diagnostics only as needed.

## Firewall baseline

For the default stack, open only what is needed:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Keep public SSH until Tailscale management is verified. Tighten later.

## Hostname and hosts file

If `sudo` warns that the host cannot be resolved, check:

```bash
hostname
cat /etc/hostname
cat /etc/hosts
```

Make `/etc/hosts` consistent with the current hostname before going deeper. This is a baseline hygiene issue, not usually a proxy issue.

## Recovery rules

Before changing SSH or firewall behavior, make sure at least one recovery path exists:
- provider web console
- Tailscale SSH or Tailscale network access
- a second active shell session

Never tighten access blindly.

## Minimal service toolbox

Use these commands constantly:

```bash
systemctl status <service> --no-pager -l
journalctl -u <service> --no-pager -n 100
systemctl cat <service>
ss -ltnp
ip -brief addr
```

## Third-party script stance

If you deliberately use a community install script, prefer download-then-run over `curl | sh`:

```bash
curl -fsSL <url> -o /tmp/install.sh
less /tmp/install.sh
bash /tmp/install.sh
rm -f /tmp/install.sh
```

Do this only when you already decided that script is worth trusting. Default stance stays manual and inspectable.

## What not to do early

Do not start with:
- control panels
- multiple proxy stacks
- reverse proxies
- domain and certificate work
- fancy automation before the manual path is understood

## Completion checklist

Before moving on, know:
- how you will get back into the machine if SSH changes go wrong
- which ports are intentionally open
- which user and path the proxy service will use
- whether Tailscale is the next step or already present
