#!/usr/bin/env bash
# Create a lightweight bundle directory that summarizes stage2 evidence inputs.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MACHINE_A_DIR=""
MACHINE_B_DIR=""
ROSBAG_PATH=""
ACCEPTANCE_DOC=""
BUNDLE_DIR=""

print_usage() {
  echo "Usage: ./scripts/create_stage2_bundle.sh --machine-a-dir path --machine-b-dir path [--rosbag-path path] [--acceptance-doc path] [--bundle-dir path]"
  echo "Example: ./scripts/create_stage2_bundle.sh --machine-a-dir artifacts/stage2_runs/run01/machine_a --machine-b-dir artifacts/stage2_runs/run01/machine_b --rosbag-path bags/stage2_run_01 --acceptance-doc docs/acceptance_stage2_20260315.md"
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --machine-a-dir)
      if [[ $# -lt 2 ]]; then
        echo "[create_stage2_bundle] ERROR: --machine-a-dir requires a path."
        print_usage
        exit 1
      fi
      MACHINE_A_DIR="$2"
      shift 2
      ;;
    --machine-b-dir)
      if [[ $# -lt 2 ]]; then
        echo "[create_stage2_bundle] ERROR: --machine-b-dir requires a path."
        print_usage
        exit 1
      fi
      MACHINE_B_DIR="$2"
      shift 2
      ;;
    --rosbag-path)
      if [[ $# -lt 2 ]]; then
        echo "[create_stage2_bundle] ERROR: --rosbag-path requires a path."
        print_usage
        exit 1
      fi
      ROSBAG_PATH="$2"
      shift 2
      ;;
    --acceptance-doc)
      if [[ $# -lt 2 ]]; then
        echo "[create_stage2_bundle] ERROR: --acceptance-doc requires a path."
        print_usage
        exit 1
      fi
      ACCEPTANCE_DOC="$2"
      shift 2
      ;;
    --bundle-dir)
      if [[ $# -lt 2 ]]; then
        echo "[create_stage2_bundle] ERROR: --bundle-dir requires a path."
        print_usage
        exit 1
      fi
      BUNDLE_DIR="$2"
      shift 2
      ;;
    *)
      echo "[create_stage2_bundle] ERROR: unknown argument '${1}'."
      print_usage
      exit 1
      ;;
  esac
done

if [[ -z "${MACHINE_A_DIR}" || -z "${MACHINE_B_DIR}" ]]; then
  echo "[create_stage2_bundle] ERROR: --machine-a-dir and --machine-b-dir are required."
  print_usage
  exit 1
fi

MACHINE_A_DIR="$(resolve_path "${MACHINE_A_DIR}")"
MACHINE_B_DIR="$(resolve_path "${MACHINE_B_DIR}")"
ROSBAG_PATH="$(resolve_path "${ROSBAG_PATH}")"
ACCEPTANCE_DOC="$(resolve_path "${ACCEPTANCE_DOC}")"

if [[ ! -d "${MACHINE_A_DIR}" ]]; then
  echo "[create_stage2_bundle] ERROR: machine A artifact directory was not found: ${MACHINE_A_DIR}"
  exit 1
fi

if [[ ! -d "${MACHINE_B_DIR}" ]]; then
  echo "[create_stage2_bundle] ERROR: machine B artifact directory was not found: ${MACHINE_B_DIR}"
  exit 1
fi

if [[ -z "${BUNDLE_DIR}" ]]; then
  BUNDLE_DIR="${WORKSPACE_DIR}/artifacts/stage2_bundle/$(date +%Y%m%d_%H%M%S)"
else
  BUNDLE_DIR="$(resolve_path "${BUNDLE_DIR}")"
fi

mkdir -p "${BUNDLE_DIR}/machine_a"
mkdir -p "${BUNDLE_DIR}/machine_b"
mkdir -p "${BUNDLE_DIR}/acceptance"

cp -a "${MACHINE_A_DIR}/." "${BUNDLE_DIR}/machine_a/"
cp -a "${MACHINE_B_DIR}/." "${BUNDLE_DIR}/machine_b/"

if [[ -n "${ACCEPTANCE_DOC}" && -f "${ACCEPTANCE_DOC}" ]]; then
  cp -a "${ACCEPTANCE_DOC}" "${BUNDLE_DIR}/acceptance/"
  ACCEPTANCE_STATUS="provided"
elif [[ -n "${ACCEPTANCE_DOC}" ]]; then
  ACCEPTANCE_STATUS="missing_at_path"
  printf "acceptance_doc_not_found=%s\n" "${ACCEPTANCE_DOC}" > "${BUNDLE_DIR}/acceptance/missing.txt"
else
  ACCEPTANCE_STATUS="not_provided"
  printf "acceptance_doc_not_provided\n" > "${BUNDLE_DIR}/acceptance/missing.txt"
fi

cat > "${BUNDLE_DIR}/bag_info.txt" <<EOF
created_at=$(date -Iseconds)
bag_path=${ROSBAG_PATH:-not_provided}
bag_exists=$([[ -n "${ROSBAG_PATH}" && -e "${ROSBAG_PATH}" ]] && echo yes || echo no)
bag_copied=no
note=rosbag data is not copied by default; only the path is recorded.
EOF

SUMMARY_FILE="${BUNDLE_DIR}/summary.txt"
cat > "${SUMMARY_FILE}" <<EOF
created_at=$(date -Iseconds)
bundle_dir=${BUNDLE_DIR}
machine_a_source=${MACHINE_A_DIR}
machine_b_source=${MACHINE_B_DIR}
acceptance_doc=${ACCEPTANCE_DOC:-not_provided}
rosbag_path=${ROSBAG_PATH:-not_provided}

provided_evidence:
- machine_a artifact directory
- machine_b artifact directory
EOF

if [[ -n "${ROSBAG_PATH}" ]]; then
  printf "%s\n" "- rosbag path record" >> "${SUMMARY_FILE}"
fi

if [[ "${ACCEPTANCE_STATUS}" == "provided" ]]; then
  printf "%s\n" "- acceptance document copy" >> "${SUMMARY_FILE}"
fi

cat >> "${SUMMARY_FILE}" <<EOF

missing_evidence:
EOF

MISSING_COUNT=0

if [[ -z "${ROSBAG_PATH}" ]]; then
  printf "%s\n" "- rosbag path not provided" >> "${SUMMARY_FILE}"
  MISSING_COUNT=$((MISSING_COUNT + 1))
elif [[ ! -e "${ROSBAG_PATH}" ]]; then
  printf "%s\n" "- rosbag path provided but not found" >> "${SUMMARY_FILE}"
  MISSING_COUNT=$((MISSING_COUNT + 1))
fi

if [[ "${ACCEPTANCE_STATUS}" == "not_provided" ]]; then
  printf "%s\n" "- acceptance document not provided" >> "${SUMMARY_FILE}"
  MISSING_COUNT=$((MISSING_COUNT + 1))
elif [[ "${ACCEPTANCE_STATUS}" == "missing_at_path" ]]; then
  printf "%s\n" "- acceptance document path provided but not found" >> "${SUMMARY_FILE}"
  MISSING_COUNT=$((MISSING_COUNT + 1))
fi

if [[ "${MISSING_COUNT}" -eq 0 ]]; then
  printf "%s\n" "- none" >> "${SUMMARY_FILE}"
fi

echo "[create_stage2_bundle] bundle directory: ${BUNDLE_DIR}"
echo "[create_stage2_bundle] summary: ${SUMMARY_FILE}"
