#!/usr/bin/env sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not on PATH" >&2
  exit 1
fi

PLUGIN_PATH="/Applications/Docker.app/Contents/Resources/cli-plugins"

if docker ps >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
fi

if [ -S "$HOME/.docker/run/docker.sock" ]; then
  export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"
fi

if [ -x "$PLUGIN_PATH/docker-compose" ]; then
  export DOCKER_CONFIG="${DOCKER_CONFIG:-/tmp/aranya-watch-docker-config}"
  mkdir -p "$DOCKER_CONFIG"
  cat > "$DOCKER_CONFIG/config.json" <<EOF
{
  "cliPluginsExtraDirs": [
    "$PLUGIN_PATH"
  ]
}
EOF
fi

if ! docker ps >/dev/null 2>&1; then
  echo "Docker daemon is not reachable. Start Docker Desktop and try again." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is not available. Check your Docker Desktop plugin setup." >&2
  exit 1
fi

exec docker compose "$@"
