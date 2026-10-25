# Optimization

Optimize only after the node is already correct.

## Optimization order

Prefer this order:
1. validate real user pain
2. measure line quality
3. check provider/IP quality
4. apply low-risk system tuning
5. tune client behavior if needed
6. replace the node if the route remains weak

## What to measure

Look for:
- baseline latency
- jitter
- packet loss
- evening peak behavior
- practical site reachability
- real download behavior across more than one destination

Treat single benchmark numbers cautiously.

## Provider and route quality

If multiple symptoms point to unstable routing, the provider or region may be the bottleneck.

Signs include:
- large latency spikes without local CPU pressure
- recurring evening slowdowns
- inconsistent behavior across the same test path
- poor performance even though the node is listening and healthy

## Low-risk Linux tuning

These are often reasonable defaults for a personal node:
- `net.core.default_qdisc = fq`
- `net.ipv4.tcp_congestion_control = bbr`
- `net.ipv4.tcp_mtu_probing = 1`

Apply only if supported by the kernel and verify that the service still behaves correctly after the change.

Do not jump straight to heavier moves such as kernel replacement, XanMod, or manual BBR v3 builds during first-pass optimization. Those are recovery-sensitive changes and do not fix a bad provider route. Use them only when:
- user explicitly wants that risk
- a recovery path exists
- basic route-quality evidence says the line itself is not main bottleneck

## Client-side optimization

After the server and route are understood, inspect:
- TUN mode behavior
- DNS configuration
- unnecessary rule complexity
- whether the client is actually selecting the intended node

## IP quality

Be careful with words like "clean".

Use them directionally:
- cloud or hosting ASNs are usually easier for services to classify as non-residential
- geo databases may disagree
- homepage reachability does not equal full unlock or perfect reputation

Judge IP quality by the user's actual target services, not by vague folklore alone.

## When to stop tuning

Stop tuning and recommend migration when:
- route quality remains poor after basic tuning
- the provider/IP quality is clearly the main complaint
- the user wants better stability more than they want to keep the exact current node

Tuning should not become an excuse to avoid replacing a bad node.
