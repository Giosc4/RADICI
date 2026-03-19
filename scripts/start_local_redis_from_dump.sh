#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DUMP_PATH="${1:-$ROOT_DIR/dump.rdb}"
REDIS_PORT="${REDIS_PORT:-6379}"
CONTAINER_NAME="${CONTAINER_NAME:-radici-redis-local}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:7.4}"

if [[ ! -f "$DUMP_PATH" ]]; then
  echo "Dump Redis non trovato: $DUMP_PATH"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker non e' installato o non e' disponibile nel PATH."
  exit 1
fi

echo "Avvio Redis locale da dump: $DUMP_PATH"
echo "Immagine Docker: $REDIS_IMAGE"
echo "Porta locale: $REDIS_PORT"

exec docker run --rm \
  --name "$CONTAINER_NAME" \
  -p "${REDIS_PORT}:6379" \
  -v "$ROOT_DIR:/data" \
  "$REDIS_IMAGE" \
  redis-server /usr/local/etc/redis/redis.conf \
  --dir /data \
  --dbfilename "$(basename "$DUMP_PATH")" \
  --appendonly no
