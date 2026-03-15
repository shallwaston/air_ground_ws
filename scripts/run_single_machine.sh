#!/usr/bin/env bash
# Run the all-in-one mock bringup on a single machine.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

print_usage() {
  echo "Usage: ./scripts/run_single_machine.sh [additional launch arguments]"
  echo "Example: ./scripts/run_single_machine.sh qos_config:=/path/to/qos_profiles.yaml"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

echo "[run_single_machine] launching ag_bringup/single_machine_mock.launch.py"
ros2 launch ag_bringup single_machine_mock.launch.py "$@"
