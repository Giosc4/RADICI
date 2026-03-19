#!/usr/bin/env bash

set -euo pipefail

# This script starts a disposable local Redis container from the canonical
# project dump stored in data/redis/. By default it runs in the foreground.
# If DETACH=true is provided, Redis is started in background mode so other
# scripts, such as start_local_stack.sh, can continue immediately.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_PATH="${1:-$ROOT_DIR/data/redis/radici-redis-dump.rdb}"
REDIS_PORT="${REDIS_PORT:-6380}"
CONTAINER_NAME="${CONTAINER_NAME:-radici-redis-local}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:7.4}"
RUNTIME_DIR="${RUNTIME_DIR:-/tmp/radici-redis-runtime}"
DETACH="${DETACH:-false}"

if [[ ! -f "$DUMP_PATH" ]]; then
  echo "Dump Redis non trovato: $DUMP_PATH"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker non e' installato o non e' disponibile nel PATH."
  exit 1
fi

# The runtime copy lives outside the repository tree so that the container
# can read a stable filename without mutating the canonical dump in place.
mkdir -p "$RUNTIME_DIR"
cp --reflink=auto -f "$DUMP_PATH" "$RUNTIME_DIR/$(basename "$DUMP_PATH")"

echo "Avvio Redis locale da dump: $DUMP_PATH"
echo "Immagine Docker: $REDIS_IMAGE"
echo "Porta locale: $REDIS_PORT"

docker_args=(
  run
  --rm
  --name "$CONTAINER_NAME"
  -p "${REDIS_PORT}:6379"
  -v "$RUNTIME_DIR:/data"
)

if [[ "$DETACH" == "true" ]]; then
  docker_args+=(-d)
fi

docker_args+=(
  "$REDIS_IMAGE"
  redis-server
  --dir /data
  --dbfilename "$(basename "$DUMP_PATH")"
  --appendonly no
)

if [[ "$DETACH" == "true" ]]; then
  docker "${docker_args[@]}" >/dev/null
  echo "Redis locale avviato in background come container: $CONTAINER_NAME"
else
  exec docker "${docker_args[@]}"
fi
