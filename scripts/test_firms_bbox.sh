#!/usr/bin/env sh
set -eu

AREA="${1:--125,24,-66,49}"
DAYS="${2:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

if [ "$#" -ge 2 ]; then
  shift 2
elif [ "$#" -eq 1 ]; then
  shift 1
fi

"$PYTHON_BIN" scripts/firms_api.py area "--area=$AREA" --days "$DAYS" "$@"
