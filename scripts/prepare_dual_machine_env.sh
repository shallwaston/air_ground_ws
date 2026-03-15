#!/usr/bin/env bash
# Print the key ROS and machine settings before a dual-machine smoke test.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_SOURCE=0

print_usage() {
  echo "Usage: ./scripts/prepare_dual_machine_env.sh [--skip-source]"
  echo "Example: ./scripts/prepare_dual_machine_env.sh"
  echo "Use --skip-source if ROS and the workspace are already sourced in the current shell."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "[prepare_dual_machine_env] ERROR: too many arguments."
  print_usage
  exit 1
fi

if [[ "${1:-}" == "--skip-source" ]]; then
  SKIP_SOURCE=1
elif [[ $# -eq 1 ]]; then
  echo "[prepare_dual_machine_env] ERROR: unknown argument '${1}'."
  print_usage
  exit 1
fi

cd "${WORKSPACE_DIR}"

if [[ ${SKIP_SOURCE} -eq 0 ]]; then
  source "${WORKSPACE_DIR}/scripts/source_ws.sh"
fi

echo "[prepare_dual_machine_env] host information"
echo "hostname: $(hostname)"
echo "hostname -I: $(hostname -I 2>/dev/null || echo unavailable)"
echo
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
