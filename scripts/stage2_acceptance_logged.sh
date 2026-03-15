#!/usr/bin/env bash
# Run the stage2 acceptance check with automatic log capture.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR=""
ENV_FILE=""

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/stage2_acceptance_logged.sh [--env-file path/to/file.env] [--artifact-dir path]"
  echo "Example: ./scripts/stage2_acceptance_logged.sh --env-file env/machine_a_default.env --artifact-dir artifacts/stage2_runs/run01/acceptance"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[stage2_acceptance_logged] ERROR: --env-file requires a path."
        print_usage
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    --artifact-dir)
      if [[ $# -lt 2 ]]; then
        echo "[stage2_acceptance_logged] ERROR: --artifact-dir requires a path."
        print_usage
        exit 1
      fi
      ARTIFACT_DIR="$2"
      shift 2
      ;;
    *)
      echo "[stage2_acceptance_logged] ERROR: unknown argument '${1}'."
      print_usage
      exit 1
      ;;
  esac
done

if [[ -z "${ARTIFACT_DIR}" ]]; then
  ARTIFACT_DIR="${WORKSPACE_DIR}/artifacts/stage2_runs/$(date +%Y%m%d_%H%M%S)/acceptance"
elif [[ "${ARTIFACT_DIR}" != /* ]]; then
  ARTIFACT_DIR="${WORKSPACE_DIR}/${ARTIFACT_DIR}"
fi

mkdir -p "${ARTIFACT_DIR}"

stage2_load_env_file "stage2_acceptance_logged" "${ENV_FILE}"
stage2_require_vars_from_env_file "stage2_acceptance_logged" "${ENV_FILE}" \
  STAGE2_MACHINE_ROLE WORKSPACE_PATH ROS_DOMAIN_ID RMW_IMPLEMENTATION
stage2_warn_workspace_path_mismatch "stage2_acceptance_logged" "${WORKSPACE_DIR}"

LOG_FILE="${ARTIFACT_DIR}/stage2_acceptance.log"
COMMAND_FILE="${ARTIFACT_DIR}/command.txt"
EXIT_CODE_FILE="${ARTIFACT_DIR}/exit_code.txt"

cat > "${COMMAND_FILE}" <<EOF
wrapper=stage2_acceptance_logged.sh
timestamp=$(date -Iseconds)
artifact_dir=${ARTIFACT_DIR}
log_file=${LOG_FILE}
env_file=${ENV_FILE:-not_provided}
command=./scripts/stage2_acceptance_check.sh
EOF

set +e
"${WORKSPACE_DIR}/scripts/run_with_log_capture.sh" --log-file "${LOG_FILE}" -- "${WORKSPACE_DIR}/scripts/stage2_acceptance_check.sh"
COMMAND_RC=$?
set -e

printf "command_exit_code=%s\n" "${COMMAND_RC}" > "${EXIT_CODE_FILE}"
exit "${COMMAND_RC}"
