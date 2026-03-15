#!/usr/bin/env bash
# Read-only validator for a stage2 bundle directory.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR=""
PASS_ITEMS=()
WARN_ITEMS=()
FAIL_ITEMS=()

print_usage() {
  echo "Usage: ./scripts/validate_stage2_bundle.sh --bundle-dir path/to/bundle"
  echo "Example: ./scripts/validate_stage2_bundle.sh --bundle-dir artifacts/stage2_bundle/run01_bundle"
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

append_item() {
  local level="$1"
  local text="$2"

  case "${level}" in
    PASS)
      PASS_ITEMS+=("${text}")
      ;;
    WARN)
      WARN_ITEMS+=("${text}")
      ;;
    FAIL)
      FAIL_ITEMS+=("${text}")
      ;;
  esac
}

has_visible_file() {
  local search_dir="$1"

  find "${search_dir}" -maxdepth 1 -type f | grep -q .
}

has_command_or_log() {
  local search_dir="$1"

  find "${search_dir}" -maxdepth 1 -type f \
    \( -name 'command.txt' -o -name '*.log' -o -name '*stdout.log' \) | grep -q .
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --bundle-dir)
      if [[ $# -lt 2 ]]; then
        echo "[validate_stage2_bundle] ERROR: --bundle-dir requires a path."
        print_usage
        exit 2
      fi
      BUNDLE_DIR="$2"
      shift 2
      ;;
    *)
      echo "[validate_stage2_bundle] ERROR: unknown argument '${1}'."
      print_usage
      exit 2
      ;;
  esac
done

if [[ -z "${BUNDLE_DIR}" ]]; then
  echo "[validate_stage2_bundle] ERROR: --bundle-dir is required."
  print_usage
  exit 2
fi

BUNDLE_DIR="$(resolve_path "${BUNDLE_DIR}")"

if [[ ! -d "${BUNDLE_DIR}" ]]; then
  echo "[validate_stage2_bundle] ERROR: bundle directory was not found: ${BUNDLE_DIR}"
  exit 2
fi

echo "[validate_stage2_bundle] bundle_dir: ${BUNDLE_DIR}"

MACHINE_A_DIR="${BUNDLE_DIR}/machine_a"
MACHINE_B_DIR="${BUNDLE_DIR}/machine_b"
ACCEPTANCE_DIR="${BUNDLE_DIR}/acceptance"
SUMMARY_FILE="${BUNDLE_DIR}/summary.txt"
BAG_INFO_FILE="${BUNDLE_DIR}/bag_info.txt"
BAG_PATH_FILE="${BUNDLE_DIR}/bag_path.txt"

if [[ -d "${MACHINE_A_DIR}" ]]; then
  append_item PASS "machine_a/ exists"
  if has_command_or_log "${MACHINE_A_DIR}"; then
    append_item PASS "machine_a/ contains command.txt or log output"
  else
    append_item WARN "machine_a/ exists but no command.txt or log file was found at the top level"
  fi
else
  append_item FAIL "machine_a/ is missing"
fi

if [[ -d "${MACHINE_B_DIR}" ]]; then
  append_item PASS "machine_b/ exists"
  if has_command_or_log "${MACHINE_B_DIR}"; then
    append_item PASS "machine_b/ contains command.txt or log output"
  else
    append_item WARN "machine_b/ exists but no command.txt or log file was found at the top level"
  fi
else
  append_item FAIL "machine_b/ is missing"
fi

if [[ -d "${ACCEPTANCE_DIR}" ]]; then
  append_item PASS "acceptance/ exists"
  if has_visible_file "${ACCEPTANCE_DIR}"; then
    if find "${ACCEPTANCE_DIR}" -maxdepth 1 -type f ! -name 'missing.txt' | grep -q .; then
      append_item PASS "acceptance/ contains at least one acceptance artifact"
    else
      append_item WARN "acceptance/ only contains placeholder or missing markers"
    fi
  else
    append_item WARN "acceptance/ exists but no files were found"
  fi
else
  append_item FAIL "acceptance/ is missing"
fi

if [[ -f "${SUMMARY_FILE}" ]]; then
  append_item PASS "summary.txt exists"
else
  append_item FAIL "summary.txt is missing"
fi

if [[ -f "${BAG_INFO_FILE}" ]]; then
  append_item PASS "bag_info.txt exists"
  if grep -q '^bag_path=not_provided$' "${BAG_INFO_FILE}"; then
    append_item WARN "bag_info.txt says bag_path=not_provided"
  elif grep -q '^bag_exists=no$' "${BAG_INFO_FILE}"; then
    append_item WARN "bag_info.txt says the provided rosbag path was not found"
  fi
elif [[ -f "${BAG_PATH_FILE}" ]]; then
  append_item PASS "bag_path.txt exists"
else
  append_item FAIL "bag_info.txt or bag_path.txt is missing"
fi

if [[ -f "${SUMMARY_FILE}" ]]; then
  if grep -q '^machine_a_source=' "${SUMMARY_FILE}" && grep -q '^machine_b_source=' "${SUMMARY_FILE}"; then
    append_item PASS "summary.txt records machine_a_source and machine_b_source"
  else
    append_item WARN "summary.txt exists but does not clearly record both machine sources"
  fi
fi

if [[ ${#FAIL_ITEMS[@]} -gt 0 ]]; then
  RESULT="FAIL"
  EXIT_CODE=1
elif [[ ${#WARN_ITEMS[@]} -gt 0 ]]; then
  RESULT="WARN"
  EXIT_CODE=1
else
  RESULT="PASS"
  EXIT_CODE=0
fi

echo "[validate_stage2_bundle] result: ${RESULT}"
echo
echo "[validate_stage2_bundle] Submission Checklist"

for item in "${PASS_ITEMS[@]}"; do
  echo "[PASS] ${item}"
done

for item in "${WARN_ITEMS[@]}"; do
  echo "[WARN] ${item}"
done

for item in "${FAIL_ITEMS[@]}"; do
  echo "[FAIL] ${item}"
done

echo
echo "[validate_stage2_bundle] Exit code guide"
echo "0 = PASS"
echo "1 = WARN or FAIL"
echo "2 = parameter error or invalid bundle root"

exit "${EXIT_CODE}"
