#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  PYTHON=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON=$(command -v python)
else
  echo "[ERROR] Python 3.10+ was not found. Install it from https://www.python.org/downloads/ and rerun." >&2
  exit 127
fi
exec "$PYTHON" "$SCRIPT_DIR/bootstrap.py" "$@"
