#!/usr/bin/env bash
# Run a semi-automatic stage2 topic visibility and telemetry check.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_DURATION_SEC="${CHECK_DURATION_SEC:-8}"

print_usage() {
  echo "Usage: ./scripts/stage2_acceptance_check.sh"
  echo "This script checks stage2 topics, then runs list / hz / bw / echo / delay probes."
  echo "Use CHECK_DURATION_SEC=<seconds> to change the timed sampling window."
}

run_timed_command() {
  local title="$1"
  shift

  echo
  echo "===== ${title} ====="
  set +e
  timeout "${CHECK_DURATION_SEC}s" "$@"
  local command_rc=$?
  set -e

  if [[ ${command_rc} -ne 0 && ${command_rc} -ne 124 ]]; then
    echo "[stage2_acceptance_check] ERROR: command failed with code ${command_rc}: $*"
    return "${command_rc}"
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "[stage2_acceptance_check] ERROR: this script does not accept positional arguments."
  print_usage
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

echo "[stage2_acceptance_check] stage2 acceptance snapshot"
echo "timestamp: $(date -Iseconds)"
echo "hostname: $(hostname)"
echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"

./scripts/validate_dual_machine_topics.sh

run_timed_command "ros2 topic list" ros2 topic list
run_timed_command "ros2 topic hz /uav/odom" ros2 topic hz /uav/odom
run_timed_command "ros2 topic bw /uav/map/tile" ros2 topic bw /uav/map/tile
run_timed_command "ros2 topic echo /uav/targets/current --once" ros2 topic echo /uav/targets/current --once

if ros2 topic delay --help >/dev/null 2>&1; then
  run_timed_command "ros2 topic delay /system/delay_probe" ros2 topic delay /system/delay_probe
else
  run_timed_command "delay probe fallback" ros2 run ag_monitor delay_probe_sub
fi
