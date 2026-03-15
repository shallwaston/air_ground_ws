#!/usr/bin/env bash
# Clear a previously applied Linux tc netem rule.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: sudo ./scripts/clear_netem.sh <iface>"
  echo "Example: sudo ./scripts/clear_netem.sh wlan0"
  exit 0
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "[clear_netem] ERROR: this script needs sudo/root."
  echo "[clear_netem] Example: sudo ./scripts/clear_netem.sh wlan0"
  exit 1
fi

IFACE="${1}"

echo "[clear_netem] clearing root qdisc on ${IFACE}"
tc qdisc del dev "${IFACE}" root 2>/dev/null || true
echo "[clear_netem] done."
