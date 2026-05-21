#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [ "$#" -lt 1 ]; then
  echo "Usage: scripts/ccproxy-switch.sh PROFILE [MODEL]" >&2
  echo "Example: scripts/ccproxy-switch.sh chatgpt-subscription ChatGPT5.5" >&2
  exit 2
fi
if [ "$#" -eq 1 ]; then
  PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy model set --provider "$1"
else
  PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy model set --provider "$1" --model "$2"
fi
