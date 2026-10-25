#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-xray}"
CONFIG_PATH="${CONFIG_PATH:-/usr/local/etc/xray/config.json}"
XRAY_BIN="${XRAY_BIN:-/usr/local/bin/xray}"
PORT="${PORT:-443}"

run() {
  local cmd="$1"
  echo
  echo "### $cmd"
  if sudo -n true >/dev/null 2>&1; then
    sudo bash -lc "$cmd"
  elif [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    bash -lc "$cmd"
  else
    bash -lc "$cmd"
  fi
}

run "date"
run "hostnamectl || true"
run "ip -brief addr || true"
run "systemctl status $SERVICE_NAME --no-pager -l || true"
run "journalctl -u $SERVICE_NAME --no-pager -n 100 || true"
run "systemctl cat $SERVICE_NAME || true"
run "pgrep -a xray || true"
run "ss -ltnp | grep -E '(:$PORT|xray)' || true"
run "ufw status verbose || true"
run "$XRAY_BIN version || true"
run "$XRAY_BIN run -test -config $CONFIG_PATH || true"
run "timeout 3 bash -lc '</dev/tcp/127.0.0.1/$PORT' && echo OPEN || echo CLOSED"
