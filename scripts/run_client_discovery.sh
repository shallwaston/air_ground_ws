#!/usr/bin/env bash
# Start the UAV/client-side stack pointing at the Fast DDS Discovery Server.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=""
SERVER_IP=""
DISCOVERY_PORT=""
EXTRA_LAUNCH_ARGS=()

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/run_client_discovery.sh [--env-file path/to/file.env] [server_ip] [port] [additional launch arguments]"
  echo "Example: ./scripts/run_client_discovery.sh --env-file env/machine_b_discovery.env"
  echo "Example: ./scripts/run_client_discovery.sh 192.168.0.10 11811"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[run_client_discovery] ERROR: --env-file requires a path."
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

if [[ $# -ge 1 ]]; then
  SERVER_IP="$1"
  shift
fi

if [[ $# -ge 1 ]]; then
  DISCOVERY_PORT="$1"
  shift
fi

EXTRA_LAUNCH_ARGS=("$@")

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

stage2_load_env_file "run_client_discovery" "${ENV_FILE}"
stage2_require_vars_from_env_file "run_client_discovery" "${ENV_FILE}" \
  STAGE2_MACHINE_ROLE WORKSPACE_PATH ROS_DOMAIN_ID RMW_IMPLEMENTATION
stage2_warn_workspace_path_mismatch "run_client_discovery" "${WORKSPACE_DIR}"

if [[ -z "${SERVER_IP}" && -n "${DISCOVERY_SERVER_IP:-}" ]]; then
  SERVER_IP="${DISCOVERY_SERVER_IP}"
fi

if [[ -z "${DISCOVERY_PORT}" && -n "${DISCOVERY_SERVER_PORT:-}" ]]; then
  DISCOVERY_PORT="${DISCOVERY_SERVER_PORT}"
fi

if [[ -z "${SERVER_IP}" || -z "${DISCOVERY_PORT}" ]]; then
  if [[ -n "${ROS_DISCOVERY_SERVER:-}" ]]; then
    stage2_parse_discovery_server_value "run_client_discovery" "${ROS_DISCOVERY_SERVER}" SERVER_IP DISCOVERY_PORT
  elif [[ -n "${ENV_FILE}" ]]; then
    echo "[run_client_discovery] ERROR: env file did not provide DISCOVERY_SERVER_IP / DISCOVERY_SERVER_PORT or ROS_DISCOVERY_SERVER."
    echo "[run_client_discovery] Next step: update the env file or pass '<server_ip> <port>' on the command line."
    exit 1
  fi
fi

SERVER_IP="${SERVER_IP:-127.0.0.1}"
DISCOVERY_PORT="${DISCOVERY_PORT:-11811}"

if [[ "${ROS_LOCALHOST_ONLY:-0}" == "1" ]]; then
  echo "[run_client_discovery] ERROR: ROS_LOCALHOST_ONLY=1 blocks dual-machine discovery."
  echo "[run_client_discovery] Next step: run 'unset ROS_LOCALHOST_ONLY' and retry."
  exit 1
fi

export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
export FASTRTPS_DEFAULT_PROFILES_FILE="${WORKSPACE_DIR}/config/fastdds/fastdds_profiles.xml"
export ROS_DISCOVERY_SERVER="${SERVER_IP}:${DISCOVERY_PORT}"

if [[ -n "${STAGE2_ENV_FILE_LOADED:-}" ]]; then
  echo "[run_client_discovery] loaded env file: ${STAGE2_ENV_FILE_LOADED}"
  echo "[run_client_discovery] STAGE2_MACHINE_ROLE=${STAGE2_MACHINE_ROLE:-unset}"
fi
echo "[run_client_discovery] RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
echo "[run_client_discovery] FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE}"
echo "[run_client_discovery] ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER}"
echo "[run_client_discovery] ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0} (must match the server machine)"
echo "[run_client_discovery] launching ag_bringup/dual_machine_client.launch.py"

ros2 launch ag_bringup dual_machine_client.launch.py "${EXTRA_LAUNCH_ARGS[@]}"
