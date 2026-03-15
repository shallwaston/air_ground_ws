#!/usr/bin/env bash
# Replay a recorded rosbag with --clock for integration testing.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: ./scripts/replay_rosbag.sh <bag_path>"
  echo "Example: ./scripts/replay_rosbag.sh bags/mock_run"
  exit 0
fi

BAG_PATH="${1}"

echo "[replay_rosbag] replaying bag: ${BAG_PATH}"
ros2 bag play "${BAG_PATH}" --clock
