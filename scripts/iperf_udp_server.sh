#!/usr/bin/env bash
# Start an iperf3 server for Wi-Fi throughput tests.

set -euo pipefail

PORT="${1:-5201}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./scripts/iperf_udp_server.sh [port]"
  echo "Example: ./scripts/iperf_udp_server.sh 5201"
  exit 0
fi

if ! command -v iperf3 >/dev/null 2>&1; then
  echo "[iperf_udp_server] ERROR: iperf3 not found."
  echo "[iperf_udp_server] Next step: sudo apt install iperf3"
  exit 1
fi

echo "[iperf_udp_server] starting iperf3 server on port ${PORT}"
iperf3 -s -p "${PORT}"
