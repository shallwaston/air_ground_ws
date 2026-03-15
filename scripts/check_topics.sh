#!/usr/bin/env bash
# Show the ROS graph and inspect the key topics used by this MVP.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_TOPICS=(
  "/system/heartbeat"
  "/uav/odom"
  "/uav/map/tile"
  "/uav/targets/current"
  "/system/delay_probe"
  "/tf"
)

print_usage() {
  echo "Usage: ./scripts/check_topics.sh [topic ...]"
  echo "Example: ./scripts/check_topics.sh /uav/odom /uav/map/tile /tf"
  echo "If no topics are given, the script inspects the default MVP topic set."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

TOPICS=("${DEFAULT_TOPICS[@]}")
if [[ $# -gt 0 ]]; then
  TOPICS=("$@")
fi

echo "[check_topics] current topic list:"
if ! TOPIC_LIST="$(ros2 topic list)"; then
  echo "[check_topics] ERROR: failed to query the ROS graph."
  echo "[check_topics] Next step: make sure the target launch file is already running and the environment was sourced correctly."
  exit 1
fi
echo "${TOPIC_LIST}"

for TOPIC in "${TOPICS[@]}"; do
  echo
  echo "[check_topics] inspecting ${TOPIC}"
  if grep -Fxq "${TOPIC}" <<<"${TOPIC_LIST}"; then
    ros2 topic info -v "${TOPIC}"
  else
    echo "[check_topics] ${TOPIC} is not discovered yet."
  fi
done
