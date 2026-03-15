#!/usr/bin/env bash
# Print the key ROS and machine settings before a dual-machine smoke test.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_SOURCE=0
ENV_FILE=""

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/prepare_dual_machine_env.sh [--skip-source] [--env-file path/to/file.env]"
  echo "Example: ./scripts/prepare_dual_machine_env.sh --env-file env/machine_a_default.env"
  echo "Use --skip-source if ROS and the workspace are already sourced in the current shell."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --skip-source)
      SKIP_SOURCE=1
      shift
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[prepare_dual_machine_env] ERROR: --env-file requires a path."
        print_usage
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    *)
      echo "[prepare_dual_machine_env] ERROR: unknown argument '${1}'."
      print_usage
      exit 1
      ;;
  esac
done

cd "${WORKSPACE_DIR}"

if [[ ${SKIP_SOURCE} -eq 0 ]]; then
  source "${WORKSPACE_DIR}/scripts/source_ws.sh"
fi

stage2_load_env_file "prepare_dual_machine_env" "${ENV_FILE}"
stage2_require_vars_from_env_file "prepare_dual_machine_env" "${ENV_FILE}" \
  STAGE2_MACHINE_ROLE WORKSPACE_PATH ROS_DOMAIN_ID RMW_IMPLEMENTATION
stage2_warn_workspace_path_mismatch "prepare_dual_machine_env" "${WORKSPACE_DIR}"

echo "[prepare_dual_machine_env] host information"
echo "hostname: $(hostname)"
echo "hostname -I: $(hostname -I 2>/dev/null || echo unavailable)"
echo
if [[ -n "${STAGE2_ENV_FILE_LOADED:-}" ]]; then
  echo "[prepare_dual_machine_env] loaded env file: ${STAGE2_ENV_FILE_LOADED}"
  echo "STAGE2_MACHINE_ROLE=${STAGE2_MACHINE_ROLE:-unset}"
  echo "WORKSPACE_PATH=${WORKSPACE_PATH:-unset}"
  echo
fi
echo "[prepare_dual_machine_env] ROS environment"
echo "ROS_DISTRO=${ROS_DISTRO:-unset}"
echo "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"
echo "ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-unset}"
echo "ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER:-unset}"

if [[ "${ROS_DISTRO:-}" != "jazzy" ]]; then
  echo "[prepare_dual_machine_env] WARNING: ROS_DISTRO is not 'jazzy'."
fi

if [[ "${ROS_LOCALHOST_ONLY:-0}" == "1" ]]; then
  echo "[prepare_dual_machine_env] WARNING: ROS_LOCALHOST_ONLY=1 blocks dual-machine visibility."
  echo "[prepare_dual_machine_env] Recommended fix: unset ROS_LOCALHOST_ONLY"
else
  echo "[prepare_dual_machine_env] localhost-only restriction is not enabled."
fi

if [[ -z "${RMW_IMPLEMENTATION:-}" ]]; then
  echo "[prepare_dual_machine_env] INFO: RMW_IMPLEMENTATION is not set. For Fast DDS tests, export rmw_fastrtps_cpp."
fi

echo
echo "[prepare_dual_machine_env] Suggested next commands"
echo "ip a"
echo "hostname"
echo "ping <peer_ip>"
echo "./scripts/net_baseline_check.sh <peer_ip>"
