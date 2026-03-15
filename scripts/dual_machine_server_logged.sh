#!/usr/bin/env bash
# Run the server-side stage2 entrypoint with automatic log capture.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR=""
ENV_FILE=""
MODE="default"
EXTRA_ARGS=()

print_usage() {
  echo "Usage: ./scripts/dual_machine_server_logged.sh [--mode default|discovery] [--env-file path/to/file.env] [--artifact-dir path] [-- additional args]"
  echo "Example: ./scripts/dual_machine_server_logged.sh --env-file env/machine_a_default.env --artifact-dir artifacts/stage2_runs/run01/machine_a"
  echo "Example: ./scripts/dual_machine_server_logged.sh --mode discovery --env-file env/machine_a_discovery.env --artifact-dir artifacts/stage2_runs/run01/machine_a"
}

format_command() {
  printf "%q " "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "[dual_machine_server_logged] ERROR: --mode requires a value."
        print_usage
        exit 1
      fi
      MODE="$2"
      shift 2
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[dual_machine_server_logged] ERROR: --env-file requires a path."
        print_usage
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    --artifact-dir)
      if [[ $# -lt 2 ]]; then
        echo "[dual_machine_server_logged] ERROR: --artifact-dir requires a path."
        print_usage
        exit 1
      fi
      ARTIFACT_DIR="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

EXTRA_ARGS=("$@")

case "${MODE}" in
  default)
    BASE_SCRIPT="${WORKSPACE_DIR}/scripts/dual_machine_server_smoke.sh"
    ;;
  discovery)
    BASE_SCRIPT="${WORKSPACE_DIR}/scripts/run_server_discovery.sh"
    ;;
  *)
    echo "[dual_machine_server_logged] ERROR: unsupported mode '${MODE}'. Use 'default' or 'discovery'."
    exit 1
    ;;
esac

if [[ -z "${ARTIFACT_DIR}" ]]; then
  ARTIFACT_DIR="${WORKSPACE_DIR}/artifacts/stage2_runs/$(date +%Y%m%d_%H%M%S)/machine_a"
elif [[ "${ARTIFACT_DIR}" != /* ]]; then
  ARTIFACT_DIR="${WORKSPACE_DIR}/${ARTIFACT_DIR}"
fi

mkdir -p "${ARTIFACT_DIR}"

LOG_FILE="${ARTIFACT_DIR}/server_stdout.log"
COMMAND_FILE="${ARTIFACT_DIR}/command.txt"
EXIT_CODE_FILE="${ARTIFACT_DIR}/exit_code.txt"

COMMAND_ARGS=("${BASE_SCRIPT}")
if [[ -n "${ENV_FILE}" ]]; then
  COMMAND_ARGS+=(--env-file "${ENV_FILE}")
fi
COMMAND_ARGS+=("${EXTRA_ARGS[@]}")

cat > "${COMMAND_FILE}" <<EOF
wrapper=dual_machine_server_logged.sh
timestamp=$(date -Iseconds)
mode=${MODE}
artifact_dir=${ARTIFACT_DIR}
log_file=${LOG_FILE}
env_file=${ENV_FILE:-not_provided}
command=$(format_command "${COMMAND_ARGS[@]}")
EOF

set +e
"${WORKSPACE_DIR}/scripts/run_with_log_capture.sh" --log-file "${LOG_FILE}" -- "${COMMAND_ARGS[@]}"
COMMAND_RC=$?
set -e

printf "command_exit_code=%s\n" "${COMMAND_RC}" > "${EXIT_CODE_FILE}"
exit "${COMMAND_RC}"
