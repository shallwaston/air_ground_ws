#!/usr/bin/env bash
# Apply Linux tc netem settings to simulate loss, delay, and jitter.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 4 ]]; then
  echo "Usage: sudo ./scripts/apply_netem.sh <iface> <loss_pct> <delay> <jitter>"
  echo "Example: sudo ./scripts/apply_netem.sh wlan0 5% 50ms 10ms"
  exit 0
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "[apply_netem] ERROR: this script needs sudo/root."
  echo "[apply_netem] Example: sudo ./scripts/apply_netem.sh wlan0 5% 50ms 10ms"
  exit 1
fi

IFACE="${1}"
LOSS_PCT="${2}"
DELAY="${3}"
JITTER="${4}"

echo "[apply_netem] applying netem on ${IFACE}: loss=${LOSS_PCT} delay=${DELAY} jitter=${JITTER}"
tc qdisc replace dev "${IFACE}" root netem loss "${LOSS_PCT}" delay "${DELAY}" "${JITTER}"
echo "[apply_netem] done. Next step: rerun topic/bandwidth/delay checks under weak-network conditions."
