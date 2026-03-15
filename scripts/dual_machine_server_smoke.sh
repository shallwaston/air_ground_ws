#!/usr/bin/env bash
# Start the default-discovery server-side smoke stack on machine A.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_ONLY=0
ENV_FILE=""
EXTRA_LAUNCH_ARGS=()

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/dual_machine_server_smoke.sh [--check-only] [--env-file path/to/file.env] [additional launch arguments]"
  echo "Example: ./scripts/dual_machine_server_smoke.sh --env-file env/machine_a_default.env"
  echo "This script prepares a default-discovery dual-machine smoke environment."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[dual_machine_server_smoke] ERROR: --env-file requires a path."
        print_usage
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

EXTRA_LAUNCH_ARGS=("$@")

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

stage2_load_env_file "dual_machine_server_smoke" "${ENV_FILE}"
stage2_require_vars_from_env_file "dual_machine_server_smoke" "${ENV_FILE}" \
  STAGE2_MACHINE_ROLE WORKSPACE_PATH ROS_DOMAIN_ID RMW_IMPLEMENTATION
stage2_warn_workspace_path_mismatch "dual_machine_server_smoke" "${WORKSPACE_DIR}"

if [[ -n "${STAGE2_ENV_FILE_LOADED:-}" && -n "${ROS_DISCOVERY_SERVER:-}" ]]; then
  echo "[dual_machine_server_smoke] INFO: env file provided ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER}, but default-discovery smoke will unset it."
fi

if [[ -n "${STAGE2_ENV_FILE_LOADED:-}" && "${ROS_LOCALHOST_ONLY:-0}" == "1" ]]; then
  echo "[dual_machine_server_smoke] INFO: env file set ROS_LOCALHOST_ONLY=1, but dual-machine smoke will unset it."
fi

unset ROS_DISCOVERY_SERVER
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

echo "[dual_machine_server_smoke] machine role: server / machine A"
echo "hostname: $(hostname)"
echo "hostname -I: $(hostname -I 2>/dev/null || echo unavailable)"
if [[ -n "${STAGE2_ENV_FILE_LOADED:-}" ]]; then
  echo "loaded env file: ${STAGE2_ENV_FILE_LOADED}"
  echo "STAGE2_MACHINE_ROLE=${STAGE2_MACHINE_ROLE:-unset}"
fi
echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
echo "ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER:-unset}"
echo "ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-unset}"
echo
echo "[dual_machine_server_smoke] This script uses default discovery, not Discovery Server."
echo "[dual_machine_server_smoke] Keep the same ROS_DOMAIN_ID on machine B."

if [[ ${CHECK_ONLY} -eq 1 ]]; then
  echo "[dual_machine_server_smoke] check-only mode enabled, no launch started."
  echo "[dual_machine_server_smoke] Next step on this machine: ros2 launch ag_bringup dual_machine_server.launch.py"
  exit 0
fi

ros2 launch ag_bringup dual_machine_server.launch.py "${EXTRA_LAUNCH_ARGS[@]}"
