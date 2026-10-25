# Migration And Rebuild

Use this when the current node should be replaced, rebuilt, or re-created.

## Common triggers

- provider or route quality is no longer acceptable
- the IP quality is the main problem
- the node has become messy enough that rebuild is cheaper than repair
- the user wants a new region or provider
- the node must be recreated after lockout or failure

## Rebuild mindset

Prefer reproducibility over heroics.

Capture the important facts before tearing anything down:
- current provider and region
- management path
- public and tailnet addresses
- firewall posture
- Xray config path and service overrides
- REALITY values and client mapping
- whether clients target public IP or tailnet IP
- any hardening or tuning already applied

Record them in `current-state.local.md` before migration work starts.

## Safe migration sequence

1. document the current node state
2. choose the replacement node and baseline architecture
3. bootstrap management access first
4. deploy the proxy plane on the new node
5. verify listener, TCP reachability, and client handshake
6. switch the client to the new node
7. only then retire the old node

## Credential strategy

When rebuilding on a new node, decide deliberately whether to:
- preserve the existing client-facing values for convenience
- or rotate UUID / REALITY materials for cleanliness and risk reduction

If secrets or configs might have leaked, rotate.

## Cutover rules

During cutover:
- keep the old node available until the new node is verified
- avoid changing both server and client structure at the same time unless necessary
- update `current-state.local.md` with the new source of truth as soon as the new node is the intended primary

## Decommission checklist

Before deleting the old node:
- confirm the new node works from the real client device
- confirm management access to the new node exists
- archive or record any values that still matter
- note the decommission decision in the state file
