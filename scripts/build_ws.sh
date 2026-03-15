#!/usr/bin/env bash
# Build the ROS 2 workspace with symlink-install for easier iteration.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLCON_ARGS=("$@")

print_usage() {
  echo "Usage: ./scripts/build_ws.sh [additional colcon build arguments]"
  echo "Example: ./scripts/build_ws.sh --packages-select ag_bringup ag_mock_nodes"
}

source_setup_file() {
  local setup_file="$1"
  local had_nounset=0

  if [[ $- == *u* ]]; then
    had_nounset=1
    set +u
  fi

  export AMENT_TRACE_SETUP_FILES="${AMENT_TRACE_SETUP_FILES:-}"
  # shellcheck disable=SC1090
  source "${setup_file}"

  if [[ ${had_nounset} -eq 1 ]]; then
    set -u
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

echo "[build_ws] workspace: ${WORKSPACE_DIR}"

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "[build_ws] ERROR: /opt/ros/jazzy/setup.bash was not found."
  echo "[build_ws] Next step: install ROS 2 Jazzy or fix your ROS installation path."
  exit 1
fi

if ! command -v colcon >/dev/null 2>&1; then
  echo "[build_ws] ERROR: colcon is not installed or not on PATH."
  echo "[build_ws] Next step: install python3-colcon-common-extensions."
  exit 1
fi

source_setup_file /opt/ros/jazzy/setup.bash
cd "${WORKSPACE_DIR}"

echo "[build_ws] running: colcon build --symlink-install ${COLCON_ARGS[*]:-}"
if ! colcon build --symlink-install "${COLCON_ARGS[@]}"; then
  echo "[build_ws] Build failed."
  echo "[build_ws] Next step: inspect the error above, fix it, then rerun this script."
  exit 1
fi

echo "[build_ws] Build succeeded."
echo "[build_ws] Next step: source install/setup.bash or run 'source scripts/source_ws.sh'."
