#!/usr/bin/env bash
# Collect a stage2 evidence snapshot into a timestamped directory.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=""
OUTPUT_DIR=""
COLLECT_TARGET_ONCE=0
COLLECT_ODOM_HZ=0
COLLECT_MAP_BW=0
SAMPLE_SECONDS="${SAMPLE_SECONDS:-8}"
RUN_FAILURES=0

# shellcheck disable=SC1091
source "${WORKSPACE_DIR}/scripts/stage2_env_helpers.sh"

print_usage() {
  echo "Usage: ./scripts/collect_stage2_evidence.sh [--env-file path/to/file.env] [--output-dir path] [--collect-target-once] [--collect-odom-hz] [--collect-map-bw] [--sample-seconds N]"
  echo "Example: ./scripts/collect_stage2_evidence.sh --env-file env/machine_a_default.env --collect-target-once --collect-odom-hz --collect-map-bw"
  echo "This script writes evidence files under artifacts/stage2_runs/<timestamp>_<host>_<role>/ by default."
}

sanitize_tag() {
  printf "%s" "$1" | tr -c 'A-Za-z0-9._-' '_'
}

append_summary() {
  printf "%s\n" "$1" >> "${SUMMARY_FILE}"
}

append_status() {
  local label="$1"
  local status_text="$2"
  printf "%-28s %s\n" "${label}" "${status_text}" >> "${STATUS_FILE}"
}

capture_command() {
  local label="$1"
  local output_file="$2"
  shift 2
  local command_rc=0

  echo "[collect_stage2_evidence] collecting ${label}"
  {
    echo "label: ${label}"
    echo "timestamp: $(date -Iseconds)"
    printf "command:"
    printf " %q" "$@"
    echo
    echo
    set +e
    "$@"
    command_rc=$?
    set -e
    echo
    echo "[exit_code] ${command_rc}"
  } > "${output_file}" 2>&1

  if [[ ${command_rc} -eq 0 ]]; then
    append_status "${label}" "OK -> $(basename "${output_file}")"
  else
    append_status "${label}" "FAILED(rc=${command_rc}) -> $(basename "${output_file}")"
    RUN_FAILURES=1
    echo "[collect_stage2_evidence] WARNING: ${label} failed with rc=${command_rc}. Output kept at ${output_file}"
  fi
}

capture_timed_command() {
  local label="$1"
  local output_file="$2"
  local sample_seconds="$3"
  shift 3
  local command_rc=0

  echo "[collect_stage2_evidence] collecting ${label} for ${sample_seconds}s"
  {
    echo "label: ${label}"
    echo "timestamp: $(date -Iseconds)"
    echo "sample_seconds: ${sample_seconds}"
    printf "command:"
    printf " %q" timeout "${sample_seconds}s" "$@"
    echo
    echo
    set +e
    timeout "${sample_seconds}s" "$@"
    command_rc=$?
    set -e
    echo
    echo "[exit_code] ${command_rc}"
  } > "${output_file}" 2>&1

  if [[ ${command_rc} -eq 0 || ${command_rc} -eq 124 ]]; then
    append_status "${label}" "OK -> $(basename "${output_file}")"
  else
    append_status "${label}" "FAILED(rc=${command_rc}) -> $(basename "${output_file}")"
    RUN_FAILURES=1
    echo "[collect_stage2_evidence] WARNING: ${label} failed with rc=${command_rc}. Output kept at ${output_file}"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "[collect_stage2_evidence] ERROR: --env-file requires a path."
        print_usage
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    --output-dir)
      if [[ $# -lt 2 ]]; then
        echo "[collect_stage2_evidence] ERROR: --output-dir requires a path."
        print_usage
        exit 1
      fi
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --collect-target-once)
      COLLECT_TARGET_ONCE=1
      shift
      ;;
    --collect-odom-hz)
      COLLECT_ODOM_HZ=1
      shift
      ;;
    --collect-map-bw)
      COLLECT_MAP_BW=1
      shift
      ;;
    --sample-seconds)
      if [[ $# -lt 2 ]]; then
        echo "[collect_stage2_evidence] ERROR: --sample-seconds requires a value."
        print_usage
        exit 1
      fi
      SAMPLE_SECONDS="$2"
      shift 2
      ;;
    *)
      echo "[collect_stage2_evidence] ERROR: unknown argument '${1}'."
      print_usage
      exit 1
      ;;
  esac
done

cd "${WORKSPACE_DIR}"
source "${WORKSPACE_DIR}/scripts/source_ws.sh"

stage2_load_env_file "collect_stage2_evidence" "${ENV_FILE}"
stage2_require_vars_from_env_file "collect_stage2_evidence" "${ENV_FILE}" \
  STAGE2_MACHINE_ROLE WORKSPACE_PATH ROS_DOMAIN_ID RMW_IMPLEMENTATION
stage2_warn_workspace_path_mismatch "collect_stage2_evidence" "${WORKSPACE_DIR}"

export ROS_HOME="${ROS_HOME:-/tmp/air_ground_ws_stage2_evidence_ros_home}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-${ROS_HOME}/log}"
mkdir -p "${ROS_LOG_DIR}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
HOST_TAG="$(sanitize_tag "$(hostname)")"
ROLE_TAG="$(sanitize_tag "${STAGE2_MACHINE_ROLE:-unknown_role}")"

if [[ -z "${OUTPUT_DIR}" ]]; then
  OUTPUT_DIR="${WORKSPACE_DIR}/artifacts/stage2_runs/${TIMESTAMP}_${HOST_TAG}_${ROLE_TAG}"
elif [[ "${OUTPUT_DIR}" != /* ]]; then
  OUTPUT_DIR="${WORKSPACE_DIR}/${OUTPUT_DIR}"
fi

mkdir -p "${OUTPUT_DIR}"

SUMMARY_FILE="${OUTPUT_DIR}/acceptance_snippet.md"
STATUS_FILE="${OUTPUT_DIR}/capture_status.txt"

cat > "${SUMMARY_FILE}" <<EOF
# Stage2 Evidence Snapshot

- timestamp: ${TIMESTAMP}
- hostname: $(hostname)
- stage2_machine_role: ${STAGE2_MACHINE_ROLE:-unset}
- env_file: ${STAGE2_ENV_FILE_LOADED:-not_provided}
- output_dir: ${OUTPUT_DIR}
- workspace_dir: ${WORKSPACE_DIR}
- ROS_DOMAIN_ID: ${ROS_DOMAIN_ID:-unset}
- RMW_IMPLEMENTATION: ${RMW_IMPLEMENTATION:-unset}
- ROS_DISCOVERY_SERVER: ${ROS_DISCOVERY_SERVER:-unset}
- ROS_LOCALHOST_ONLY: ${ROS_LOCALHOST_ONLY:-unset}

## Capture Status

EOF

: > "${STATUS_FILE}"

cat > "${OUTPUT_DIR}/ros_env_summary.txt" <<EOF
timestamp=$(date -Iseconds)
hostname=$(hostname)
stage2_machine_role=${STAGE2_MACHINE_ROLE:-unset}
env_file=${STAGE2_ENV_FILE_LOADED:-not_provided}
workspace_dir=${WORKSPACE_DIR}
workspace_path_from_env=${WORKSPACE_PATH:-unset}
ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-unset}
RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}
ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER:-unset}
ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-unset}
ROS_HOME=${ROS_HOME}
ROS_LOG_DIR=${ROS_LOG_DIR}
EOF

append_status "ros_env_summary" "OK -> ros_env_summary.txt"

capture_command "hostname" "${OUTPUT_DIR}/hostname.txt" hostname
capture_command "date" "${OUTPUT_DIR}/date.txt" date -Iseconds
capture_command "uname -a" "${OUTPUT_DIR}/uname_a.txt" uname -a
capture_command "ip a" "${OUTPUT_DIR}/ip_a.txt" ip a
capture_command "ros2 node list" "${OUTPUT_DIR}/ros2_node_list.txt" ros2 node list
capture_command "ros2 topic list" "${OUTPUT_DIR}/ros2_topic_list.txt" ros2 topic list

if [[ ${COLLECT_TARGET_ONCE} -eq 1 ]]; then
  capture_command "ros2 topic echo /uav/targets/current --once" \
    "${OUTPUT_DIR}/uav_targets_current_once.txt" \
    timeout "${SAMPLE_SECONDS}s" ros2 topic echo /uav/targets/current --once
else
  append_status "target_once" "SKIPPED"
fi

if [[ ${COLLECT_ODOM_HZ} -eq 1 ]]; then
  capture_timed_command "ros2 topic hz /uav/odom" \
    "${OUTPUT_DIR}/uav_odom_hz.txt" "${SAMPLE_SECONDS}" \
    ros2 topic hz /uav/odom
else
  append_status "uav_odom_hz" "SKIPPED"
fi

if [[ ${COLLECT_MAP_BW} -eq 1 ]]; then
  capture_timed_command "ros2 topic bw /uav/map/tile" \
    "${OUTPUT_DIR}/uav_map_tile_bw.txt" "${SAMPLE_SECONDS}" \
    ros2 topic bw /uav/map/tile
else
  append_status "uav_map_tile_bw" "SKIPPED"
fi

append_summary '```text'
cat "${STATUS_FILE}" >> "${SUMMARY_FILE}"
append_summary '```'
append_summary ""
append_summary "## Suggested Acceptance References"
append_summary ""
append_summary "- env summary: \`$(basename "${OUTPUT_DIR}")/ros_env_summary.txt\`"
append_summary "- topic list: \`$(basename "${OUTPUT_DIR}")/ros2_topic_list.txt\`"
append_summary "- node list: \`$(basename "${OUTPUT_DIR}")/ros2_node_list.txt\`"
append_summary "- full status: \`$(basename "${OUTPUT_DIR}")/capture_status.txt\`"

echo "[collect_stage2_evidence] evidence directory: ${OUTPUT_DIR}"
if [[ ${RUN_FAILURES} -ne 0 ]]; then
  echo "[collect_stage2_evidence] completed with warnings. See ${STATUS_FILE} for failed items."
else
  echo "[collect_stage2_evidence] completed successfully."
fi
