#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [ "$#" -lt 1 ]; then
  echo "Usage: scripts/ccproxy-switch.sh PROFILE" >&2
  echo "Example: scripts/ccproxy-switch.sh openai-key" >&2
  exit 2
fi
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy use "$@"
