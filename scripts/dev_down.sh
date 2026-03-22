#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$ROOT_DIR"

if [ "${1:-}" = "--volumes" ]; then
  sh "$SCRIPT_DIR/docker_compose.sh" down --remove-orphans -v
else
  sh "$SCRIPT_DIR/docker_compose.sh" down --remove-orphans
fi

echo
echo "aranya-watch has been stopped."
