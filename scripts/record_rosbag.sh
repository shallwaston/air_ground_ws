#!/usr/bin/env bash
# Record the key MVP topics into a rosbag.

set -euo pipefail

OUTPUT_DIR="${1:-bags/mock_run}"

echo "[record_rosbag] output directory: ${OUTPUT_DIR}"
echo "[record_rosbag] recording key topics. Press Ctrl+C to stop."
ros2 bag record \
  /system/heartbeat \
  /system/delay_probe \
  /uav/odom \
  /uav/map/tile \
  /uav/targets/current \
  -o "${OUTPUT_DIR}"
