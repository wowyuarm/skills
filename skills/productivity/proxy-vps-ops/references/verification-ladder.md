# Verification Ladder

Use this ladder to prove where the problem actually is.

Do not skip ahead. Move from the lowest unproven layer upward.

## 0. Establish execution context

First decide:
- are you on the VPS?
- are you on the local client machine?
- do you only have guided-commands mode?

Record the context in the state file if it changes.

## 1. Service process exists

On the VPS:

```bash
systemctl status xray --no-pager -l
pgrep -a xray
```

Question answered: is the service running at all?

## 2. Config validates

```bash
/usr/local/bin/xray run -test -config /usr/local/etc/xray/config.json
```

Question answered: is the config syntactically valid?

## 3. Listener exists

```bash
ss -ltnp | grep ':443'
ss -ltnp | grep xray
```

Question answered: did the process actually bind the intended port?

This is a separate question from service health.

## 4. Local TCP connect works on the VPS

```bash
timeout 3 bash -lc '</dev/tcp/127.0.0.1/443' && echo OPEN || echo CLOSED
```

Question answered: can the VPS itself connect to the listener?

If this fails with `Connection refused`, do not blame the client.

## 5. Firewall and exposure are correct

```bash
ufw status verbose
```

Also check provider-level security groups if applicable.

Question answered: is the path allowed to reach the listener?

## 6. Public TCP connect works

From outside the VPS, or from the user machine:

```bash
Test-NetConnection <public-ip> -Port 443
```

or:

```bash
timeout 5 bash -lc '</dev/tcp/<public-ip>/443' && echo OPEN || echo CLOSED
```

Question answered: is the node externally reachable at the TCP layer?

## 7. Handshake fields match

Only after TCP reachability is proven, check:
- UUID
- port
- `servername`
- REALITY public key
- short ID
- `flow: xtls-rprx-vision`
- correct address: public IP vs tailnet IP

Question answered: are client and server speaking the same configuration?

## 8. Client routing / DNS / TUN works

Only after the node itself is good, inspect:
- selected proxy group
- TUN mode
- system proxy state
- DNS behavior
- rules selecting the wrong path

Question answered: is the client actually using the node as intended?

## Symptom mapping

### `connection refused`
Usually points to layers 3-4 first:
- no listener
- wrong port
- process bound nowhere

### `timeout`
Usually points to layers 5-6 first:
- firewall or security group
- wrong address
- network path problem

### handshake failure
Usually points to layer 7:
- REALITY mismatch
- wrong client fields

### node works but traffic fails
Usually points to layer 8:
- client routing
- DNS
- TUN
- local policy issues

## Golden rule

Before editing the client, prove whether the VPS is listening and reachable.
