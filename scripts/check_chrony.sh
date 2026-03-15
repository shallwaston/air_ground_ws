#!/usr/bin/env bash
# Print Chrony tracking information for time-sync validation.

set -euo pipefail

print_usage() {
  echo "Usage: ./scripts/check_chrony.sh"
  echo "This script checks whether chronyc exists, then prints tracking and sources."
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "[check_chrony] ERROR: this script does not accept positional arguments."
  print_usage
  exit 1
fi

if ! command -v chronyc >/dev/null 2>&1; then
  echo "[check_chrony] chronyc was not found on PATH."
  echo "[check_chrony] Next step: install chrony on this machine, or record time-sync evidence manually."
  exit 1
fi

echo "[check_chrony] chronyc path: $(command -v chronyc)"
echo
echo "[check_chrony] chronyc tracking"
chronyc tracking
echo
echo "[check_chrony] chronyc sources"
chronyc sources
