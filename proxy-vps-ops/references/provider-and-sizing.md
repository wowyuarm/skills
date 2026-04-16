# Provider And Sizing

## What matters most

For a personal proxy node, prioritize:
1. route quality from the user's location
2. evening stability
3. packet loss and jitter
4. support quality and rebuild convenience
5. only then advertised bandwidth

A mediocre line with a fancy protocol still feels mediocre.

## Region heuristics

Use regional choice as a latency and policy tradeoff, not as a dogma.

- **Singapore:** Common default for East and Southeast Asia. Often practical, not automatically best.
- **Japan:** Often worth testing for lower latency or cleaner routes depending on the user's ISP.
- **Hong Kong:** Can be excellent or disappointing depending on provider and route quality.
- **US West:** Usually higher latency but sometimes preferable for specific services or IP reputation.

Prefer real measurement over folklore. If possible, test at least one alternative region before treating the first node as permanent.

## Shared CPU vs dedicated CPU

### Shared CPU
Use as the default for a personal node.

Good when:
- single user or small number of devices
- light to moderate traffic
- cost sensitivity matters
- the main uncertainty is network quality, not compute

### Dedicated CPU / VDS
Consider only if evidence shows a real need:
- consistent noisy-neighbor symptoms
- sustained high throughput or many simultaneous users
- CPU contention affecting performance
- predictable production-grade workload

For most personal proxy use, **network quality dominates CPU class**.

## Memory and disk

A typical starting point is enough:
- **1 vCPU / 2 GB RAM / 40-50 GB disk** is usually fine for a single-user Xray + Tailscale node.
- Upgrade only if evidence shows memory pressure, extra workloads, or broader multi-user use.

## Bandwidth billing vs traffic billing

### Bandwidth billing
Prefer this when:
- the node will stay on for daily use
- the user wants predictable bills
- the user does not want to watch monthly transfer closely

### Traffic billing
Prefer this when:
- the node is for short experiments
- usage is truly light or temporary
- the provider's traffic pricing is materially better and acceptable

If unsure, bandwidth-style pricing is often easier operationally.

## Provider evaluation checklist

Before committing long term, answer:
- how does the route behave during evening peak hours?
- how easy is reinstall or rebuild?
- does the provider expose a usable web console?
- how clear are billing and outbound-transfer rules?
- is IPv4 included and stable?
- how painful is IP or region replacement?

## Baseline validation strategy

If the user is unsure about a provider or region:
1. create a minimal node
2. establish management access
3. perform simple route and stability checks
4. optionally use a simpler tunnel baseline such as WireGuard to test the line
5. only then invest in the full public proxy stack

## When to replace instead of tune

Lean toward replacing the node when:
- evening jitter or packet loss is persistent
- multiple services see the same instability
- route quality remains poor after simple system tuning
- the provider/IP quality becomes the main complaint

Do not spend unlimited time tuning around a fundamentally weak route.
