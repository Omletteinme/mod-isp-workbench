#!/bin/sh
set -eu

APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_DIR=${MOD_ISP_VENV:-"$APP_DIR/.venv"}

if [ ! -x "$VENV_DIR/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$APP_DIR/requirements-runtime.txt"
cd "$APP_DIR"
exec "$VENV_DIR/bin/python" app.py
