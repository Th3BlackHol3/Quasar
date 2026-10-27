#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Quasar is not set up yet. Run: $SCRIPT_DIR/setup.sh" >&2
  exit 2
fi
exec "$PYTHON" "$SCRIPT_DIR/quasar.py" "$@"
