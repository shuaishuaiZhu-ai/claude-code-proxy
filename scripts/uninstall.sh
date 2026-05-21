#!/usr/bin/env sh
set -eu

KEEP_STATE=0
for arg in "$@"; do
    case "$arg" in
        --keep-state) KEEP_STATE=1 ;;
        *)
            echo "usage: scripts/uninstall.sh [--keep-state]" >&2
            exit 2
            ;;
    esac
done

step() {
    printf '[ccproxy] %s\n' "$1"
}

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

step "uninstalling package with pip uninstall"
if PYTHON="$(find_python)"; then
    "$PYTHON" -m pip uninstall -y claude-code-proxy
else
    echo "warning: Python was not found, so pip uninstall could not run." >&2
fi

STATE_DIR="$HOME/.ccproxy"
if [ "$KEEP_STATE" -eq 1 ]; then
    step "keeping state directory: $STATE_DIR"
elif [ -e "$STATE_DIR" ]; then
    step "removing state directory: $STATE_DIR"
    rm -rf "$STATE_DIR"
else
    step "state directory not found: $STATE_DIR"
fi

step "uninstall complete. This script does not uninstall Python, pip, or Claude CLI."
step "It does not uninstall Python, pip, or Claude without user confirmation."
