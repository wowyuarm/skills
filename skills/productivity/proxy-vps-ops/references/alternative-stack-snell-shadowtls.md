# Alternative Stack: Snell + ShadowTLS

Use this reference only when the user explicitly wants a Surge / Snell path.

Do not silently replace the default Xray + VLESS + REALITY path with this stack.

## When this stack makes sense

Good fit when:
- user already uses Surge and wants native Snell config lines
- user explicitly asks for Snell
- user wants to test Snell v4 or v5 behavior
- user wants ShadowTLS as extra camouflage in front of Snell

Usually not worth it when:
- user is happy with Mihomo / Clash Verge Rev
- user needs widest cross-platform client compatibility
- user wants most common community path for debugging and migration

## Baseline choices

Prefer this order:
1. Snell v4 as stable baseline
2. Snell v5 only if client support is confirmed and user wants its newer features
3. ShadowTLS v3 only when user explicitly wants it or line conditions justify trying it

Do not add ShadowTLS by reflex. First decide whether plain Snell already meets the goal.

## Clean service shape

Preferred layout:
- Tailscale for management plane
- Snell as upstream proxy service
- optional ShadowTLS as public-facing wrapper in front of Snell
- UFW exposes only intended public port

If ShadowTLS is used, cleaner shape is:
- public client -> ShadowTLS public port
- ShadowTLS -> local Snell upstream port
- management still goes through Tailscale / SSH

When practical, do not leave raw Snell port publicly exposed if ShadowTLS is intended to be public entry point.

## Client coupling warning

This stack is more client-coupled than default Xray path.

Practical reading:
- strong fit for Surge users
- weaker fit for generic Mihomo-first workflows
- debugging help and community examples are usually narrower than Xray + REALITY

Choose it because user needs it, not because installer looks easy.

## Server-side checklist

For plain Snell:
- confirm installed binary version
- confirm service unit name and config path
- confirm listener port with `ss -ltnp`
- confirm firewall policy for that port
- output client values only after listener is proven

For Snell + ShadowTLS:
- confirm Snell upstream listener exists
- confirm ShadowTLS public listener exists
- confirm ShadowTLS forwards to intended Snell port
- confirm raw Snell port exposure matches intended policy
- verify client uses ShadowTLS values, not raw Snell values, when testing wrapped path

## Verification order

Use same layered thinking as default stack:
1. service state
2. listener state
3. local TCP reachability
4. external TCP reachability
5. client handshake correctness
6. client policy / routing behavior

Useful checks:

```bash
systemctl status snell --no-pager -l
journalctl -u snell --no-pager -n 100
ss -ltnp | grep -E ':(443|8443|<snell-port>|<shadowtls-port>)'
ufw status verbose
```

If multiple per-port units exist, inspect exact unit name instead of assuming single `snell.service`.

## Multi-user stance

Only add multi-user layout if user truly needs it.

If needed, clean model is:
- one config per user / port
- one systemd unit per exposed port
- explicit mapping of port -> credential -> client
- state file records every active port and intended owner / device

Do not introduce multi-user layout during first-pass debugging of a single-user node.

## ShadowTLS specifics

Pick SNI target deliberately:
- public
- stable
- normal TLS site
- sensible for user region

Do not cargo-cult one domain forever. If handshake or reachability looks odd, test another stable TLS host.

## Optimization caution

BBR, kernel swaps, and other system tuning remain secondary here too.

If Snell path feels slow:
- first verify route quality
- then verify server listener correctness
- then verify client settings
- only then try low-risk system tuning

## Migration rule

If user is moving from Xray path to Snell path or back:
- keep management plane unchanged
- change one proxy stack at a time
- verify new stack before removing old one
- record final chosen stack and client values in `current-state.local.md`
