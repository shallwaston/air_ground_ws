#!/usr/bin/env bash
# Start the UGV/server-side stack with Fast DDS Discovery Server environment variables.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_DISCOVERY_SERVER="${START_DISCOVERY_SERVER:-1}"
DISCOVERY_PID=""
ENV_FILE=""
SERVER_IP=""
DISCOVERY_PORT=""
EXTRA_LAUNCH_ARGS=()

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/run_server_discovery.sh [--env-file path/to/file.env] [server_ip] [port] [additional launch arguments]"
  echo "Example: ./scripts/run_server_discovery.sh --env-file env/machine_a_discovery.env"
  echo "Example: ./scripts/run_server_discovery.sh 192.168.0.10 11811"
  echo "Tip: set START_DISCOVERY_SERVER=0 if the Discovery Server is already running elsewhere."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[run_server_discovery] ERROR: --env-file requires a path."
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

cleanup() {
  if [[ -n "${DISCOVERY_PID}" ]]; then
    echo "[run_server_discovery] stopping local discovery server pid=${DISCOVERY_PID}"
    kill "${DISCOVERY_PID}" >/dev/null 2>&1 || true
    wait "${DISCOVERY_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

stage2_load_env_file "run_server_discovery" "${ENV_FILE}"
stage2_require_vars_from_env_file "run_server_discovery" "${ENV_FILE}" \
  STAGE2_MACHINE_ROLE WORKSPACE_PATH ROS_DOMAIN_ID RMW_IMPLEMENTATION
stage2_warn_workspace_path_mismatch "run_server_discovery" "${WORKSPACE_DIR}"

if [[ -z "${SERVER_IP}" && -n "${DISCOVERY_SERVER_IP:-}" ]]; then
  SERVER_IP="${DISCOVERY_SERVER_IP}"
fi

if [[ -z "${DISCOVERY_PORT}" && -n "${DISCOVERY_SERVER_PORT:-}" ]]; then
  DISCOVERY_PORT="${DISCOVERY_SERVER_PORT}"
fi

if [[ -z "${SERVER_IP}" || -z "${DISCOVERY_PORT}" ]]; then
  if [[ -n "${ROS_DISCOVERY_SERVER:-}" ]]; then
    stage2_parse_discovery_server_value "run_server_discovery" "${ROS_DISCOVERY_SERVER}" SERVER_IP DISCOVERY_PORT
  elif [[ -n "${ENV_FILE}" ]]; then
    echo "[run_server_discovery] ERROR: env file did not provide DISCOVERY_SERVER_IP / DISCOVERY_SERVER_PORT or ROS_DISCOVERY_SERVER."
    echo "[run_server_discovery] Next step: update the env file or pass '<server_ip> <port>' on the command line."
    exit 1
  fi
fi

SERVER_IP="${SERVER_IP:-127.0.0.1}"
DISCOVERY_PORT="${DISCOVERY_PORT:-11811}"

if [[ "${ROS_LOCALHOST_ONLY:-0}" == "1" ]]; then
  echo "[run_server_discovery] ERROR: ROS_LOCALHOST_ONLY=1 blocks dual-machine discovery."
  echo "[run_server_discovery] Next step: run 'unset ROS_LOCALHOST_ONLY' and retry."
  exit 1
fi

export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
export FASTRTPS_DEFAULT_PROFILES_FILE="${WORKSPACE_DIR}/config/fastdds/fastdds_profiles.xml"
export ROS_DISCOVERY_SERVER="${SERVER_IP}:${DISCOVERY_PORT}"

if [[ -n "${STAGE2_ENV_FILE_LOADED:-}" ]]; then
  echo "[run_server_discovery] loaded env file: ${STAGE2_ENV_FILE_LOADED}"
  echo "[run_server_discovery] STAGE2_MACHINE_ROLE=${STAGE2_MACHINE_ROLE:-unset}"
fi
echo "[run_server_discovery] RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
echo "[run_server_discovery] FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE}"
echo "[run_server_discovery] ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER}"
echo "[run_server_discovery] ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0} (must match every client machine)"

if [[ "${START_DISCOVERY_SERVER}" == "1" ]]; then
  if command -v fastdds >/dev/null 2>&1; then
    echo "[run_server_discovery] fastdds path: $(command -v fastdds)"
    echo "[run_server_discovery] starting local discovery server on port ${DISCOVERY_PORT}"
    fastdds discovery -i 0 -l "${DISCOVERY_PORT}" &
    DISCOVERY_PID="$!"
    sleep 1
  else
    echo "[run_server_discovery] WARNING: fastdds CLI not found. Skipping local discovery server startup."
    echo "[run_server_discovery] If another terminal already runs the server, you can continue."
    echo "[run_server_discovery] Otherwise install the Fast DDS CLI or start only the server-side ROS stack for wiring checks."
  fi
fi

echo "[run_server_discovery] launching ag_bringup/dual_machine_server.launch.py"
ros2 launch ag_bringup dual_machine_server.launch.py "${EXTRA_LAUNCH_ARGS[@]}"
