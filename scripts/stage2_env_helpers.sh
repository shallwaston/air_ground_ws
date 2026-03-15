#!/usr/bin/env bash
# Common helpers for optional stage2 env-file loading and validation.

stage2_resolve_env_file_path() {
  local env_file_path="$1"

  if [[ -z "${env_file_path}" ]]; then
    echo ""
    return 0
  fi

  if [[ "${env_file_path}" == /* ]]; then
    echo "${env_file_path}"
  else
    echo "$(pwd)/${env_file_path}"
  fi
}

stage2_load_env_file() {
  local caller_name="$1"
  local env_file_path="$2"
  local resolved_env_file=""
  local had_allexport=0

  if [[ -z "${env_file_path}" ]]; then
    return 0
  fi

  resolved_env_file="$(stage2_resolve_env_file_path "${env_file_path}")"

  if [[ ! -f "${resolved_env_file}" ]]; then
    echo "[${caller_name}] ERROR: env file was not found: ${resolved_env_file}"
    echo "[${caller_name}] Next step: copy one of env/*.env.example files and edit it for the real machines."
    return 1
  fi

  echo "[${caller_name}] loading env file: ${resolved_env_file}"

  if [[ $- == *a* ]]; then
    had_allexport=1
  fi

  set -a
  # shellcheck disable=SC1090
  source "${resolved_env_file}"
  if [[ ${had_allexport} -eq 0 ]]; then
    set +a
  fi

  export STAGE2_ENV_FILE_LOADED="${resolved_env_file}"
}

stage2_require_vars_from_env_file() {
  local caller_name="$1"
  local env_file_path="$2"
  shift 2
  local missing_vars=()
  local var_name=""

  if [[ -z "${env_file_path}" ]]; then
    return 0
  fi

  for var_name in "$@"; do
    if [[ -z "${!var_name:-}" ]]; then
      missing_vars+=("${var_name}")
    fi
  done

  if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "[${caller_name}] ERROR: env file is missing required variables: ${missing_vars[*]}"
    echo "[${caller_name}] Next step: update ${STAGE2_ENV_FILE_LOADED:-${env_file_path}} and retry."
    return 1
  fi
}

stage2_warn_workspace_path_mismatch() {
  local caller_name="$1"
  local actual_workspace_dir="$2"

  if [[ -z "${STAGE2_ENV_FILE_LOADED:-}" || -z "${WORKSPACE_PATH:-}" ]]; then
    return 0
  fi

  if [[ "${WORKSPACE_PATH}" != "${actual_workspace_dir}" ]]; then
    echo "[${caller_name}] INFO: WORKSPACE_PATH from env file is '${WORKSPACE_PATH}'."
    echo "[${caller_name}] INFO: current script workspace is '${actual_workspace_dir}'."
    echo "[${caller_name}] INFO: this does not stop the script, but the env file should be updated before a real dual-machine run."
  fi
}

stage2_parse_discovery_server_value() {
  local caller_name="$1"
  local discovery_value="$2"
  local host_var_name="$3"
  local port_var_name="$4"
  local discovery_host=""
  local discovery_port=""

  if [[ -z "${discovery_value}" ]]; then
    echo "[${caller_name}] ERROR: ROS_DISCOVERY_SERVER is empty."
    return 1
  fi

  if [[ "${discovery_value}" != *:* ]]; then
    echo "[${caller_name}] ERROR: ROS_DISCOVERY_SERVER must use host:port format, got '${discovery_value}'."
    return 1
  fi

  discovery_host="${discovery_value%:*}"
  discovery_port="${discovery_value##*:}"

  if [[ -z "${discovery_host}" || -z "${discovery_port}" ]]; then
    echo "[${caller_name}] ERROR: ROS_DISCOVERY_SERVER must include both host and port, got '${discovery_value}'."
    return 1
  fi

  printf -v "${host_var_name}" "%s" "${discovery_host}"
  printf -v "${port_var_name}" "%s" "${discovery_port}"
}
