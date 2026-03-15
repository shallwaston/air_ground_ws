#!/usr/bin/env bash
# Wrapper around ros2 topic hz with a beginner-friendly default topic.

set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./scripts/check_hz.sh [topic]"
  echo "Example: ./scripts/check_hz.sh /uav/odom"
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "[check_hz] ERROR: too many arguments."
  echo "[check_hz] Usage: ./scripts/check_hz.sh [topic]"
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

TOPIC="${1:-/uav/odom}"
echo "[check_hz] measuring topic frequency for ${TOPIC}"
ros2 topic hz "${TOPIC}"
