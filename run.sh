#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$DIR/venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || command -v python)"
fi
exec "$PY" "$DIR/main.py"