#!/usr/bin/env bash
# Start the UAV/client-side stack pointing at the Fast DDS Discovery Server.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_IP="127.0.0.1"
DISCOVERY_PORT="11811"
EXTRA_LAUNCH_ARGS=()

print_usage() {
  echo "Usage: ./scripts/run_client_discovery.sh [server_ip] [port] [additional launch arguments]"
  echo "Example: ./scripts/run_client_discovery.sh 192.168.0.10 11811"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -ge 1 ]]; then
  SERVER_IP="$1"
  shift
fi

if [[ $# -ge 1 ]]; then
  DISCOVERY_PORT="$1"
  shift
fi

EXTRA_LAUNCH_ARGS=("$@")

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

if [[ "${ROS_LOCALHOST_ONLY:-0}" == "1" ]]; then
  echo "[run_client_discovery] ERROR: ROS_LOCALHOST_ONLY=1 blocks dual-machine discovery."
  echo "[run_client_discovery] Next step: run 'unset ROS_LOCALHOST_ONLY' and retry."
  exit 1
fi

export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE="${WORKSPACE_DIR}/config/fastdds/fastdds_profiles.xml"
export ROS_DISCOVERY_SERVER="${SERVER_IP}:${DISCOVERY_PORT}"

echo "[run_client_discovery] RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
echo "[run_client_discovery] FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE}"
echo "[run_client_discovery] ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER}"
echo "[run_client_discovery] ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0} (must match the server machine)"
echo "[run_client_discovery] launching ag_bringup/dual_machine_client.launch.py"

ros2 launch ag_bringup dual_machine_client.launch.py "${EXTRA_LAUNCH_ARGS[@]}"
