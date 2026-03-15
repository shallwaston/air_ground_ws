#!/usr/bin/env bash
# Start the default-discovery client-side smoke stack on machine B.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_ONLY=0
EXTRA_LAUNCH_ARGS=()

print_usage() {
  echo "Usage: ./scripts/dual_machine_client_smoke.sh [--check-only] [additional launch arguments]"
  echo "Example: ./scripts/dual_machine_client_smoke.sh"
  echo "This script prepares a default-discovery dual-machine smoke environment."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ "${1:-}" == "--check-only" ]]; then
  CHECK_ONLY=1
  shift
fi

EXTRA_LAUNCH_ARGS=("$@")

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

echo "[dual_machine_client_smoke] machine role: client / machine B"
echo "hostname: $(hostname)"
echo "hostname -I: $(hostname -I 2>/dev/null || echo unavailable)"
echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
echo "ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER:-unset}"
echo "ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-unset}"
echo
echo "[dual_machine_client_smoke] This script uses default discovery, not Discovery Server."
echo "[dual_machine_client_smoke] Keep the same ROS_DOMAIN_ID on machine A."

if [[ ${CHECK_ONLY} -eq 1 ]]; then
  echo "[dual_machine_client_smoke] check-only mode enabled, no launch started."
  echo "[dual_machine_client_smoke] Next step on this machine: ros2 launch ag_bringup dual_machine_client.launch.py"
  exit 0
fi

ros2 launch ag_bringup dual_machine_client.launch.py "${EXTRA_LAUNCH_ARGS[@]}"
