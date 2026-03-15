#!/usr/bin/env bash
# Run the custom TF healthcheck node once and exit.

set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./scripts/check_tf.sh"
  echo "This runs ag_tf_tools/tf_healthcheck in one-shot mode."
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "[check_tf] ERROR: this script does not accept positional arguments."
  echo "[check_tf] Usage: ./scripts/check_tf.sh"
  exit 1
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

echo "[check_tf] running tf_healthcheck in one-shot mode"
ros2 run ag_tf_tools tf_healthcheck --ros-args -p one_shot:=true -p check_period_sec:=1.0
