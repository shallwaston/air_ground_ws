#!/usr/bin/env bash
# Check whether the key stage2 topics exist in the current ROS graph.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRED_TOPICS=(
  "/uav/odom"
  "/uav/map/tile"
  "/uav/targets/current"
  "/system/delay_probe"
  "/tf"
)

print_usage() {
  echo "Usage: ./scripts/validate_dual_machine_topics.sh"
  echo "This checks whether the key stage2 topics exist in the ROS graph."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "[validate_dual_machine_topics] ERROR: this script does not accept positional arguments."
  print_usage
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

if ! TOPIC_LIST="$(ros2 topic list)"; then
  echo "[validate_dual_machine_topics] ERROR: failed to query topics."
  echo "[validate_dual_machine_topics] Next step: make sure the server/client smoke launch is running."
  exit 1
fi

echo "[validate_dual_machine_topics] discovered topics:"
echo "${TOPIC_LIST}"
echo

MISSING_TOPICS=()
for topic_name in "${REQUIRED_TOPICS[@]}"; do
  if grep -Fxq "${topic_name}" <<<"${TOPIC_LIST}"; then
    echo "[validate_dual_machine_topics] OK: ${topic_name}"
  else
    echo "[validate_dual_machine_topics] MISSING: ${topic_name}"
    MISSING_TOPICS+=("${topic_name}")
  fi
done

if [[ ${#MISSING_TOPICS[@]} -gt 0 ]]; then
  echo
  echo "[validate_dual_machine_topics] Missing topics: ${MISSING_TOPICS[*]}"
  exit 1
fi

echo
echo "[validate_dual_machine_topics] All required stage2 topics are present."
