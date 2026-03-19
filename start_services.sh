#!/usr/bin/env bash

set -euo pipefail

# This script only starts the Flask application layer.
# It does not provision Redis and assumes the datastore is already reachable.
# Use start_local_stack.sh if you want a one-command local bootstrap.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/RADICI"
BACKEND_DIR="$ROOT_DIR/backend"

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtualenv non trovato in: $VENV_DIR"
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/app.py" ]]; then
  echo "Backend non trovato in: $BACKEND_DIR"
  exit 1
fi

source "$VENV_DIR/bin/activate"

cleanup() {
  # Ensure the background Flask process is terminated if the wrapper script exits.
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Virtualenv attivato: $VENV_DIR"
echo "Avvio backend Flask su porta ${FLASK_PORT:-8080}..."
(
  # We run from backend/ so relative paths inside app.py keep behaving predictably.
  cd "$BACKEND_DIR"
  python app.py
) &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend servito direttamente dal backend Flask."
echo "Assicurati che Redis sia disponibile su ${REDIS_HOST:-127.0.0.1}:${REDIS_PORT:-6379}."
echo "Se vuoi usare il dump locale, avvia prima: ./run_local_redis_from_dump.sh"
echo "Dump atteso in: data/redis/radici-redis-dump.rdb"
echo "URL locale previsto: https://localhost:${FLASK_PORT:-8080}"
echo "Servizio avviato. Premi Ctrl+C per fermarlo."

wait "$BACKEND_PID"
