#!/usr/bin/env bash
set -euo pipefail

XRAY_BIN="${XRAY_BIN:-/usr/local/bin/xray}"
SERVER_NAME="${1:-www.cloudflare.com}"
DEST="${2:-${SERVER_NAME}:443}"

if [[ ! -x "$XRAY_BIN" ]]; then
  if command -v xray >/dev/null 2>&1; then
    XRAY_BIN="$(command -v xray)"
  else
    echo "xray binary not found at $XRAY_BIN and not available in PATH" >&2
    exit 1
  fi
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required" >&2
  exit 1
fi

uuid="$($XRAY_BIN uuid)"
keys="$($XRAY_BIN x25519)"
private_key="$(awk -F': ' '/Private key/ {print $2}' <<<"$keys")"
public_key="$(awk -F': ' '/Public key/ {print $2}' <<<"$keys")"
short_id="$(openssl rand -hex 8)"

if [[ -z "$private_key" || -z "$public_key" ]]; then
  echo "failed to parse x25519 output:" >&2
  echo "$keys" >&2
  exit 1
fi

cat <<EOF
UUID=$uuid
PRIVATE_KEY=$private_key
PUBLIC_KEY=$public_key
SHORT_ID=$short_id
SERVER_NAME=$SERVER_NAME
DEST=$DEST

# Xray config placeholders
#   id           -> $uuid
#   privateKey   -> $private_key
#   shortIds[0]  -> $short_id
#   dest         -> $DEST
#   serverNames  -> $SERVER_NAME

# Mihomo / Clash placeholders
#   uuid                         -> $uuid
#   servername                   -> $SERVER_NAME
#   reality-opts.public-key      -> $public_key
#   reality-opts.short-id        -> $short_id
EOF
