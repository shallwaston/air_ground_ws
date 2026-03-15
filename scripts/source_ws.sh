#!/usr/bin/env bash
# Source the ROS 2 Jazzy environment and this workspace overlay.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "[source_ws] Please source this script instead of executing it."
  echo "[source_ws] Example: source scripts/source_ws.sh"
  exit 1
fi

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "[source_ws] ERROR: /opt/ros/jazzy/setup.bash was not found."
  return 1
fi

source_setup_file /opt/ros/jazzy/setup.bash

if [[ -f "${WORKSPACE_DIR}/install/setup.bash" ]]; then
  source_setup_file "${WORKSPACE_DIR}/install/setup.bash"
  echo "[source_ws] ROS 2 Jazzy and workspace overlay loaded."
  echo "[source_ws] ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
  if [[ "${ROS_LOCALHOST_ONLY:-0}" == "1" ]]; then
    echo "[source_ws] WARNING: ROS_LOCALHOST_ONLY=1 only works for single-machine local tests."
    echo "[source_ws] WARNING: For dual-machine tests, run: unset ROS_LOCALHOST_ONLY"
  fi
else
  echo "[source_ws] install/setup.bash not found yet."
  echo "[source_ws] Next step: run ./scripts/build_ws.sh first."
  return 1
fi
