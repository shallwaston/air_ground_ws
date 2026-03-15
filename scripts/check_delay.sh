#!/usr/bin/env bash
# Prefer ros2 topic delay when available, otherwise fall back to the custom delay probe subscriber.

set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./scripts/check_delay.sh [topic]"
  echo "Example: ./scripts/check_delay.sh /system/delay_probe"
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "[check_delay] ERROR: too many arguments."
  echo "[check_delay] Usage: ./scripts/check_delay.sh [topic]"
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

TOPIC="${1:-/system/delay_probe}"

if ros2 topic delay --help >/dev/null 2>&1; then
  echo "[check_delay] using ros2 topic delay for ${TOPIC}"
  ros2 topic delay "${TOPIC}"
  exit 0
fi

echo "[check_delay] ros2 topic delay is not available in this environment."

if [[ "${TOPIC}" != "/system/delay_probe" ]]; then
  echo "[check_delay] Fallback mode only supports /system/delay_probe."
  echo "[check_delay] Next step: launch delay_probe_pub, then rerun without a custom topic argument."
  exit 1
fi

echo "[check_delay] falling back to ag_monitor delay_probe_sub."
echo "[check_delay] Make sure /system/delay_probe is already being published."
ros2 run ag_monitor delay_probe_sub
