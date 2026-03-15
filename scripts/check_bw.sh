#!/usr/bin/env bash
# Wrapper around ros2 topic bw with a beginner-friendly default topic.

set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./scripts/check_bw.sh [topic]"
  echo "Example: ./scripts/check_bw.sh /uav/map/tile"
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "[check_bw] ERROR: too many arguments."
  echo "[check_bw] Usage: ./scripts/check_bw.sh [topic]"
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

TOPIC="${1:-/uav/map/tile}"
echo "[check_bw] measuring topic bandwidth for ${TOPIC}"
ros2 topic bw "${TOPIC}"
