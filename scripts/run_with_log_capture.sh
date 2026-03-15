#!/usr/bin/env bash
# Run any command while teeing stdout/stderr to a log file and preserving the command exit code.

set -euo pipefail

LOG_FILE=""
COMMAND_ARGS=()

print_usage() {
  echo "Usage: ./scripts/run_with_log_capture.sh --log-file path/to/file.log -- <command> [args...]"
  echo "Example: ./scripts/run_with_log_capture.sh --log-file artifacts/stage2_runs/run01/server_stdout.log -- ./scripts/dual_machine_server_smoke.sh --env-file env/machine_a_default.env"
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
    --log-file)
      if [[ $# -lt 2 ]]; then
        echo "[run_with_log_capture] ERROR: --log-file requires a path."
        print_usage
        exit 1
      fi
      LOG_FILE="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "[run_with_log_capture] ERROR: unknown argument '${1}'."
      print_usage
      exit 1
      ;;
  esac
done

if [[ -z "${LOG_FILE}" ]]; then
  echo "[run_with_log_capture] ERROR: --log-file is required."
  print_usage
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "[run_with_log_capture] ERROR: no command was provided after '--'."
  print_usage
  exit 1
fi

COMMAND_ARGS=("$@")
mkdir -p "$(dirname "${LOG_FILE}")"

echo "[run_with_log_capture] log file: ${LOG_FILE}"
echo "[run_with_log_capture] command: $(format_command "${COMMAND_ARGS[@]}")"

{
  echo "[run_with_log_capture] started_at: $(date -Iseconds)"
  echo "[run_with_log_capture] log_file: ${LOG_FILE}"
  echo "[run_with_log_capture] command: $(format_command "${COMMAND_ARGS[@]}")"
  echo
} | tee "${LOG_FILE}"

set +e
"${COMMAND_ARGS[@]}" 2>&1 | tee -a "${LOG_FILE}"
PIPE_RC=("${PIPESTATUS[@]}")
set -e

COMMAND_RC="${PIPE_RC[0]}"
TEE_RC="${PIPE_RC[1]}"

{
  echo
  echo "[run_with_log_capture] finished_at: $(date -Iseconds)"
  echo "[run_with_log_capture] command_exit_code: ${COMMAND_RC}"
} | tee -a "${LOG_FILE}"

if [[ "${TEE_RC}" -ne 0 ]]; then
  echo "[run_with_log_capture] ERROR: failed to write the log file."
  exit "${TEE_RC}"
fi

exit "${COMMAND_RC}"
