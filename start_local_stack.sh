#!/usr/bin/env bash

set -euo pipefail

# This script is the recommended local entry point for development.
# It orchestrates the two pieces the application needs in the common case:
# 1. a local Redis instance restored from the canonical RDB dump
# 2. the Flask application that serves both backend APIs and frontend pages
#
# Behavior:
# - if the Redis container is already running, it reuses it
# - otherwise it starts Redis in background mode
# - it then launches the Flask application through start_services.sh
# - on exit, it stops Redis only if this script started Redis itself

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDIS_PORT="${REDIS_PORT:-6380}"
CONTAINER_NAME="${CONTAINER_NAME:-radici-redis-local}"
STARTED_REDIS="false"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker non e' installato o non e' disponibile nel PATH."
  exit 1
fi

if docker ps --filter "name=${CONTAINER_NAME}" --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Redis locale gia' attivo: $CONTAINER_NAME"
else
  echo "Avvio Redis locale da dump sulla porta ${REDIS_PORT}..."
  DETACH=true REDIS_PORT="$REDIS_PORT" "$ROOT_DIR/run_local_redis_from_dump.sh"
  STARTED_REDIS="true"
  sleep 2
fi

cleanup() {
  if [[ "$STARTED_REDIS" == "true" ]]; then
    echo
    echo "Arresto Redis locale avviato da questo script..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

echo "Avvio stack locale con REDIS_PORT=${REDIS_PORT}"
echo "Frontend e API saranno serviti da Flask su: https://$(hostname -I 2>/dev/null | awk '{print $1}' || echo localhost):${FLASK_PORT:-8080}"
echo "Se stai lavorando sulla stessa macchina, puoi usare anche: https://localhost:${FLASK_PORT:-8080}"
REDIS_PORT="$REDIS_PORT" "$ROOT_DIR/start_services.sh"
