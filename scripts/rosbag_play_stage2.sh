#!/usr/bin/env bash
# Replay a stage2 rosbag with --clock and friendly reminders.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

print_usage() {
  echo "Usage: ./scripts/rosbag_play_stage2.sh <bag_path>"
  echo "Example: ./scripts/rosbag_play_stage2.sh bags/stage2_run_01"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -ne 1 ]]; then
  echo "[rosbag_play_stage2] ERROR: exactly one bag path is required."
  print_usage
  exit 1
fi

BAG_PATH="$1"

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

echo "[rosbag_play_stage2] replaying bag: ${BAG_PATH}"
echo "[rosbag_play_stage2] Suggested parallel checks:"
echo "  ./scripts/check_hz.sh /uav/odom"
echo "  ./scripts/check_bw.sh /uav/map/tile"
echo "  ./scripts/check_delay.sh /system/delay_probe"
echo "  ros2 topic echo /uav/targets/current --once"
ros2 bag play "${BAG_PATH}" --clock
