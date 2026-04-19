# Troubleshooting

Troubleshoot by symptom and layer, not by random config editing.

## First rule

Before changing anything, ask:
- what exact symptom is observed?
- where was it observed: local client, local machine, VPS, or provider console?
- what layer is still unproven?

Then use the verification ladder.

## Symptom: `connection refused`

Most likely layers:
- listener missing
- wrong port
- service active but not bound

Check in order:
1. `systemctl status xray --no-pager -l`
2. `/usr/local/bin/xray run -test -config ...`
3. `systemctl cat xray`
4. `ss -ltnp | grep ':443'`
5. local TCP connect on the VPS

If the service is active but not listening, compare:
- systemd execution
- foreground manual execution
- privileged port behavior

## Symptom: timeout

Most likely layers:
- firewall or security group
- wrong public IP
- route or reachability problem
- provider-side filtering

Check in order:
1. `ss -ltnp`
2. `ufw status verbose`
3. provider-level exposure rules
4. external TCP connect tests

## Symptom: handshake failure or node selected but unusable

Most likely layers:
- wrong REALITY public key
- wrong short ID
- wrong `servername`
- wrong `flow`
- wrong address type: public IP vs tailnet IP

Only inspect these after raw TCP reachability is proven.

## Symptom: service active but no listener

This is a high-value branch. Focus on runtime environment.

Check:
- service user
- capabilities
- sandboxing or systemd overrides
- foreground root execution
- temporary non-privileged port isolation such as `8443`

Do not assume config syntax validation proves bind success.

## Symptom: client shows "connected" (with latency number) but no sites load

This looks like handshake-level failure even though the client UI says it is connected. Happens often with iOS Shadowrocket and REALITY.

Mechanism: clients report a latency number as soon as raw TCP 443 accepts. REALITY happily accepts any TCP 443 connection because its fallback forwards unknown handshakes to the disguised `dest` (for example `www.cloudflare.com:443`). So the client's latency test succeeds, the client marks the node "connected", but the actual VLESS handshake silently fails because a REALITY field is wrong or missing.

Decisive check: read the Xray journal and filter by the client's real IP. If the client has been connecting for several minutes and no log line shows its source IP inside `from <ip>:<port> accepted tcp:...`, the client's VLESS handshake never reached the proxy logic. Do not edit server config. Fix the client.

Most common client-side causes for this pattern:
- URL import dropped one of `flow`, `publicKey`, `shortId`, or `fingerprint`
- client's REALITY field name differs from the URL param name and the import silently ignored it
- older client version has partial REALITY support

Fix: manually enter every REALITY field in the client UI, do not rely on URL / QR import. If the app still fails after manual entry, switch to a client with first-class REALITY support (for example V2Box on iOS).

## Symptom: client works but speed is poor

Most likely causes:
- weak provider route
- evening congestion
- jitter or packet loss
- IP quality or upstream limitations
- client DNS/TUN side effects

Do not jump straight to protocol changes. Evaluate the line first.

## Minimal-change rule

When you identify a plausible root cause:
- apply the smallest change that addresses it
- verify immediately
- avoid redesigning the whole stack while debugging one symptom

## Evidence ranking

Prefer direct evidence in roughly this order:
1. listener state
2. local TCP reachability
3. external TCP reachability
4. foreground process error output
5. systemd logs
6. client GUI error summaries

## Recovery stance

If the node is already working, do not destabilize it for cleanup or elegance without a reason and a verification plan.
