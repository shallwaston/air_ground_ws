#!/usr/bin/env bash
# Run an iperf3 UDP client against the server machine.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: ./scripts/iperf_udp_client.sh <server_ip> [bandwidth] [duration_sec] [port]"
  echo "Example: ./scripts/iperf_udp_client.sh 192.168.0.10 50M 30 5201"
  exit 0
fi

SERVER_IP="${1}"
BANDWIDTH="${2:-50M}"
DURATION_SEC="${3:-30}"
PORT="${4:-5201}"

if ! command -v iperf3 >/dev/null 2>&1; then
  echo "[iperf_udp_client] ERROR: iperf3 not found."
  echo "[iperf_udp_client] Next step: sudo apt install iperf3"
  exit 1
fi

echo "[iperf_udp_client] target=${SERVER_IP} bandwidth=${BANDWIDTH} duration=${DURATION_SEC}s port=${PORT}"
iperf3 -u -c "${SERVER_IP}" -b "${BANDWIDTH}" -t "${DURATION_SEC}" -p "${PORT}"
