#!/usr/bin/env bash
# Initialize a stage2 run directory and print a copy-paste-friendly command plan.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ID=""
BASE_DIR="${WORKSPACE_DIR}/artifacts/stage2_runs"
MODE="default"
MACHINE_A_ENV=""
MACHINE_B_ENV=""
DISCOVERY_ENV=""

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/init_stage2_run.sh [--run-id name] [--base-dir path] [--mode default|discovery] [--machine-a-env path] [--machine-b-env path] [--discovery-env path]"
  echo "Example: ./scripts/init_stage2_run.sh --run-id wired_smoke_01 --machine-a-env env/machine_a_default.env --machine-b-env env/machine_b_default.env"
  echo "Example: ./scripts/init_stage2_run.sh --mode discovery --machine-a-env env/machine_a_discovery.env --machine-b-env env/machine_b_discovery.env"
}

resolve_path() {
  local input_path="$1"

  if [[ -z "${input_path}" ]]; then
    echo ""
  elif [[ "${input_path}" == /* ]]; then
    echo "${input_path}"
  else
    echo "${WORKSPACE_DIR}/${input_path}"
  fi
}

format_command() {
  printf "%q " "$@"
}

warn_env_path() {
  local label="$1"
  local display_path="$2"
  local resolved_path="$3"

  if [[ -z "${display_path}" ]]; then
    echo "[init_stage2_run] WARNING: ${label} was not provided."
    return 0
  fi

  if [[ ! -f "${resolved_path}" ]]; then
    echo "[init_stage2_run] WARNING: ${label} does not exist yet: ${display_path}"
    echo "[init_stage2_run] WARNING: update the env path or create the file before running on the real machines."
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --run-id)
      if [[ $# -lt 2 ]]; then
        echo "[init_stage2_run] ERROR: --run-id requires a value."
        print_usage
        exit 1
      fi
      RUN_ID="$2"
      shift 2
      ;;
    --base-dir)
      if [[ $# -lt 2 ]]; then
        echo "[init_stage2_run] ERROR: --base-dir requires a path."
        print_usage
        exit 1
      fi
      BASE_DIR="$2"
      shift 2
      ;;
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "[init_stage2_run] ERROR: --mode requires a value."
        print_usage
        exit 1
      fi
      MODE="$2"
      shift 2
      ;;
    --machine-a-env)
      if [[ $# -lt 2 ]]; then
        echo "[init_stage2_run] ERROR: --machine-a-env requires a path."
        print_usage
        exit 1
      fi
      MACHINE_A_ENV="$2"
      shift 2
      ;;
    --machine-b-env)
      if [[ $# -lt 2 ]]; then
        echo "[init_stage2_run] ERROR: --machine-b-env requires a path."
        print_usage
        exit 1
      fi
      MACHINE_B_ENV="$2"
      shift 2
      ;;
    --discovery-env)
      if [[ $# -lt 2 ]]; then
        echo "[init_stage2_run] ERROR: --discovery-env requires a path."
        print_usage
        exit 1
      fi
      DISCOVERY_ENV="$2"
      shift 2
      ;;
    *)
      echo "[init_stage2_run] ERROR: unknown argument '${1}'."
      print_usage
      exit 1
      ;;
  esac
done

case "${MODE}" in
  default|discovery)
    ;;
  *)
    echo "[init_stage2_run] ERROR: unsupported mode '${MODE}'. Use 'default' or 'discovery'."
    exit 1
    ;;
esac

cd "${WORKSPACE_DIR}"

if [[ -z "${RUN_ID}" ]]; then
  RUN_ID="$(date +%Y%m%d_%H%M%S)"
fi

BASE_DIR="$(resolve_path "${BASE_DIR}")"
RUN_ROOT="${BASE_DIR}/${RUN_ID}"
MACHINE_A_DIR="${RUN_ROOT}/machine_a"
MACHINE_B_DIR="${RUN_ROOT}/machine_b"
ACCEPTANCE_DIR="${RUN_ROOT}/acceptance"
BUNDLE_DIR="${RUN_ROOT}/bundle"
NOTES_DIR="${RUN_ROOT}/notes"

mkdir -p "${MACHINE_A_DIR}" "${MACHINE_B_DIR}" "${ACCEPTANCE_DIR}" "${BUNDLE_DIR}" "${NOTES_DIR}"

DEFAULT_MACHINE_A_ENV="env/machine_a_default.env"
DEFAULT_MACHINE_B_ENV="env/machine_b_default.env"
DEFAULT_DISCOVERY_A_ENV="env/machine_a_discovery.env"
DEFAULT_DISCOVERY_B_ENV="env/machine_b_discovery.env"

DISCOVERY_ENV_DISPLAY="${DISCOVERY_ENV}"
if [[ -z "${DISCOVERY_ENV_DISPLAY}" && "${MODE}" == "discovery" ]]; then
  DISCOVERY_ENV_DISPLAY="env/discovery_server.env"
fi

if [[ "${MODE}" == "default" ]]; then
  MACHINE_A_ENV_DISPLAY="${MACHINE_A_ENV:-${DEFAULT_MACHINE_A_ENV}}"
  MACHINE_B_ENV_DISPLAY="${MACHINE_B_ENV:-${DEFAULT_MACHINE_B_ENV}}"
else
  MACHINE_A_ENV_DISPLAY="${MACHINE_A_ENV:-${DISCOVERY_ENV:-${DEFAULT_DISCOVERY_A_ENV}}}"
  MACHINE_B_ENV_DISPLAY="${MACHINE_B_ENV:-${DISCOVERY_ENV:-${DEFAULT_DISCOVERY_B_ENV}}}"
fi

MACHINE_A_ENV_RESOLVED="$(resolve_path "${MACHINE_A_ENV_DISPLAY}")"
MACHINE_B_ENV_RESOLVED="$(resolve_path "${MACHINE_B_ENV_DISPLAY}")"
DISCOVERY_ENV_RESOLVED="$(resolve_path "${DISCOVERY_ENV_DISPLAY}")"

warn_env_path "machine A env file" "${MACHINE_A_ENV_DISPLAY}" "${MACHINE_A_ENV_RESOLVED}"
warn_env_path "machine B env file" "${MACHINE_B_ENV_DISPLAY}" "${MACHINE_B_ENV_RESOLVED}"

if [[ "${MODE}" == "discovery" ]]; then
  warn_env_path "discovery env reference" "${DISCOVERY_ENV_DISPLAY}" "${DISCOVERY_ENV_RESOLVED}"
elif [[ -n "${DISCOVERY_ENV}" ]]; then
  echo "[init_stage2_run] WARNING: --discovery-env was provided in default mode and will only be recorded in notes."
fi

if [[ "${MODE}" == "default" ]]; then
  SERVER_MODE_ARGS=()
  CLIENT_MODE_ARGS=()
else
  SERVER_MODE_ARGS=(--mode discovery)
  CLIENT_MODE_ARGS=(--mode discovery)
fi

MACHINE_A_COMMAND=(
  "./scripts/dual_machine_server_logged.sh"
  "${SERVER_MODE_ARGS[@]}"
  "--env-file" "${MACHINE_A_ENV_DISPLAY}"
  "--artifact-dir" "${MACHINE_A_DIR}"
)

MACHINE_B_COMMAND=(
  "./scripts/dual_machine_client_logged.sh"
  "${CLIENT_MODE_ARGS[@]}"
  "--env-file" "${MACHINE_B_ENV_DISPLAY}"
  "--artifact-dir" "${MACHINE_B_DIR}"
)

ACCEPTANCE_COMMAND=(
  "./scripts/stage2_acceptance_logged.sh"
  "--env-file" "${MACHINE_A_ENV_DISPLAY}"
  "--artifact-dir" "${ACCEPTANCE_DIR}"
)

MACHINE_A_EVIDENCE_COMMAND=(
  "./scripts/collect_stage2_evidence.sh"
  "--env-file" "${MACHINE_A_ENV_DISPLAY}"
  "--output-dir" "${MACHINE_A_DIR}/evidence"
  "--collect-target-once"
  "--collect-odom-hz"
  "--collect-map-bw"
)

MACHINE_B_EVIDENCE_COMMAND=(
  "./scripts/collect_stage2_evidence.sh"
  "--env-file" "${MACHINE_B_ENV_DISPLAY}"
  "--output-dir" "${MACHINE_B_DIR}/evidence"
  "--collect-target-once"
  "--collect-odom-hz"
  "--collect-map-bw"
)

BUNDLE_COMMAND=(
  "./scripts/create_stage2_bundle.sh"
  "--machine-a-dir" "${MACHINE_A_DIR}"
  "--machine-b-dir" "${MACHINE_B_DIR}"
  "--bundle-dir" "${BUNDLE_DIR}/final_bundle"
)

VALIDATE_BUNDLE_COMMAND=(
  "./scripts/validate_stage2_bundle.sh"
  "--bundle-dir" "${BUNDLE_DIR}/final_bundle"
)

cat > "${RUN_ROOT}/README.txt" <<EOF
stage2 run_id=${RUN_ID}
mode=${MODE}
run_root=${RUN_ROOT}

directories:
- machine_a/: machine A logs and evidence
- machine_b/: machine B logs and evidence
- acceptance/: acceptance command output
- bundle/: final bundle output
- notes/: manual notes, screenshots list, acceptance doc copies

recommended env files:
- machine_a=${MACHINE_A_ENV_DISPLAY}
- machine_b=${MACHINE_B_ENV_DISPLAY}
- discovery_reference=${DISCOVERY_ENV_DISPLAY:-not_provided}

see command_plan.txt for the suggested execution order.
EOF

cat > "${RUN_ROOT}/command_plan.txt" <<EOF
run_root=${RUN_ROOT}
mode=${MODE}

[machine_a]
$(format_command "${MACHINE_A_COMMAND[@]}")
$(format_command "${MACHINE_A_EVIDENCE_COMMAND[@]}")

[machine_b]
$(format_command "${MACHINE_B_COMMAND[@]}")
$(format_command "${MACHINE_B_EVIDENCE_COMMAND[@]}")

[acceptance]
$(format_command "${ACCEPTANCE_COMMAND[@]}")

[bundle]
$(format_command "${BUNDLE_COMMAND[@]}")
$(format_command "${VALIDATE_BUNDLE_COMMAND[@]}")
EOF

cat > "${NOTES_DIR}/README.txt" <<EOF
Use this directory to keep:
- copied acceptance documents
- screenshot names
- manual test notes
- operator observations that were not captured by scripts
EOF

echo "[init_stage2_run] run root: ${RUN_ROOT}"
echo "[init_stage2_run] command plan: ${RUN_ROOT}/command_plan.txt"
echo
echo "[init_stage2_run] Machine A"
echo "$(format_command "${MACHINE_A_COMMAND[@]}")"
echo "$(format_command "${MACHINE_A_EVIDENCE_COMMAND[@]}")"
echo
echo "[init_stage2_run] Machine B"
echo "$(format_command "${MACHINE_B_COMMAND[@]}")"
echo "$(format_command "${MACHINE_B_EVIDENCE_COMMAND[@]}")"
echo
echo "[init_stage2_run] Acceptance"
echo "$(format_command "${ACCEPTANCE_COMMAND[@]}")"
echo
echo "[init_stage2_run] Bundle"
echo "$(format_command "${BUNDLE_COMMAND[@]}")"
echo "$(format_command "${VALIDATE_BUNDLE_COMMAND[@]}")"
