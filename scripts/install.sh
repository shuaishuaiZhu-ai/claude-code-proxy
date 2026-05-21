#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
WITH_SERVER=0
NO_INIT=0

for arg in "$@"; do
    case "$arg" in
        --with-server) WITH_SERVER=1 ;;
        --no-init) NO_INIT=1 ;;
        *)
            echo "usage: scripts/install.sh [--with-server] [--no-init]" >&2
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
            if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    done
    echo "Python 3.11 or newer was not found. Install Python from https://www.python.org/downloads/ and rerun this script." >&2
    return 1
}

step "checking Python 3.11+"
PYTHON="$(find_python)"
"$PYTHON" --version

step "checking pip"
if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    step "pip was not available; trying Python ensurepip"
    "$PYTHON" -m ensurepip --upgrade
fi

if command -v claude >/dev/null 2>&1; then
    step "Claude CLI found: $(command -v claude)"
else
    echo "warning: Claude CLI was not found on PATH. Install it before running ccproxy through Claude Code." >&2
fi

INSTALL_TARGET="$REPO_ROOT"
if [ "$WITH_SERVER" -eq 1 ]; then
    INSTALL_TARGET="$REPO_ROOT[server]"
fi

step "installing this project with pip install -e"
"$PYTHON" -m pip install -e "$INSTALL_TARGET"

step "verifying ccproxy command"
ccproxy --version

if [ "$NO_INIT" -eq 0 ]; then
    step "preparing default config without provider login"
    ccproxy init --skip-model-set
fi

step "install complete. Try: ccproxy doctor"
