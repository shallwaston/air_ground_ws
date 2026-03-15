#!/usr/bin/env bash
# Print a beginner-friendly wired-network baseline checklist.

set -euo pipefail

print_usage() {
  echo "Usage: ./scripts/net_baseline_check.sh <peer_ip>"
  echo "Example: ./scripts/net_baseline_check.sh 192.168.0.20"
  echo "This script does not change system configuration. It only prints suggested commands."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -ne 1 ]]; then
  echo "[net_baseline_check] ERROR: exactly one peer IP is required."
  print_usage
  exit 1
fi

PEER_IP="$1"

echo "[net_baseline_check] local host information"
echo "hostname: $(hostname)"
echo "hostname -I: $(hostname -I 2>/dev/null || echo unavailable)"
echo
echo "[net_baseline_check] Suggested basic network commands"
echo "ip a"
echo "hostname"
echo "ping -c 4 ${PEER_IP}"
echo

if command -v iperf3 >/dev/null 2>&1; then
  echo "[net_baseline_check] iperf3 detected at: $(command -v iperf3)"
  echo "[net_baseline_check] Suggested TCP baseline commands"
  echo "  Server side: iperf3 -s"
  echo "  Client side: iperf3 -c ${PEER_IP}"
  echo
  echo "[net_baseline_check] Suggested UDP baseline commands"
  echo "  Server side: ./scripts/iperf_udp_server.sh"
  echo "  Client side: ./scripts/iperf_udp_client.sh ${PEER_IP} 50M 30 5201"
else
  echo "[net_baseline_check] iperf3 is not installed on this machine."
  echo "[net_baseline_check] Next step: install iperf3, then rerun this script."
  echo "[net_baseline_check] You can still use ping first: ping -c 4 ${PEER_IP}"
fi
