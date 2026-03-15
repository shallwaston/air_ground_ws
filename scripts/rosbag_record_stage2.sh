#!/usr/bin/env bash
# Record the key stage2 topics for dual-machine smoke and replay.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-bags/stage2_smoke}"

print_usage() {
  echo "Usage: ./scripts/rosbag_record_stage2.sh [output_dir]"
  echo "Example: ./scripts/rosbag_record_stage2.sh bags/stage2_run_01"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "[rosbag_record_stage2] ERROR: too many arguments."
  print_usage
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

echo "[rosbag_record_stage2] output directory: ${OUTPUT_DIR}"
echo "[rosbag_record_stage2] recording stage2 topics. Press Ctrl+C to stop."
ros2 bag record \
  /uav/odom \
  /uav/map/tile \
  /uav/targets/current \
  /system/delay_probe \
  /tf \
  /tf_static \
  -o "${OUTPUT_DIR}"
