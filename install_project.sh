#!/usr/bin/env bash

set -euo pipefail

# Full local installer for RADICI.
# It prepares:
# - the Python virtual environment
# - runtime and data-pipeline Python dependencies
# - a local .env.local when missing
# - the Redis Docker image
# - an optional local Redis container restored from the canonical dump
#
# The script is intentionally idempotent:
# - it reuses the existing virtualenv if already present
# - it does not overwrite an existing .env.local
# - it reuses an already running Redis container when present

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/RADICI}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REDIS_IMAGE="${REDIS_IMAGE:-redis:7.4}"
REDIS_PORT="${REDIS_PORT:-6380}"
CONTAINER_NAME="${CONTAINER_NAME:-radici-redis-local}"
DUMP_PATH="${DUMP_PATH:-$ROOT_DIR/data/redis/radici-redis-dump.rdb}"
INSTALL_PIPELINE_DEPS="${INSTALL_PIPELINE_DEPS:-true}"
PRELOAD_NLTK_DATA="${PRELOAD_NLTK_DATA:-true}"
SETUP_ENV_LOCAL="${SETUP_ENV_LOCAL:-true}"
START_REDIS="${START_REDIS:-true}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

fail() {
  printf '\n[ERROR] %s\n' "$1" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  local help_message="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "$help_message"
  fi
}

log "Checking local prerequisites"
require_command "$PYTHON_BIN" "Python 3 is required. Set PYTHON_BIN if it is installed under a different command."
require_command docker "Docker is required to restore and run the local Redis snapshot."

if [[ ! -f "$DUMP_PATH" ]]; then
  fail "Redis dump not found at $DUMP_PATH"
fi

if [[ ! -d "$ROOT_DIR/backend" ]] || [[ ! -f "$ROOT_DIR/backend/app.py" ]]; then
  fail "The backend application was not found under $ROOT_DIR/backend"
fi

if [[ ! -f "$ROOT_DIR/backend/requirements.txt" ]]; then
  fail "Missing backend requirements file"
fi

if [[ "$INSTALL_PIPELINE_DEPS" == "true" ]] && [[ ! -f "$ROOT_DIR/data_pipeline/requirements.txt" ]]; then
  fail "Missing data pipeline requirements file"
fi

log "Creating or reusing the project virtual environment"
if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

log "Upgrading pip tooling inside the virtual environment"
python -m pip install --upgrade pip setuptools wheel

log "Installing backend runtime dependencies"
python -m pip install -r "$ROOT_DIR/backend/requirements.txt"

if [[ "$INSTALL_PIPELINE_DEPS" == "true" ]]; then
  log "Installing active data-pipeline dependencies"
  python -m pip install -r "$ROOT_DIR/data_pipeline/requirements.txt"
fi

if [[ "$PRELOAD_NLTK_DATA" == "true" ]]; then
  log "Preloading NLTK resources used by the application"
  python - <<'PY'
import nltk

for resource in ("stopwords", "punkt", "punkt_tab"):
    try:
        nltk.download(resource, quiet=True)
        print(f"Downloaded NLTK resource: {resource}")
    except Exception as exc:
        print(f"Warning: could not download NLTK resource {resource}: {exc}")
PY
fi

if [[ "$SETUP_ENV_LOCAL" == "true" ]] && [[ ! -f "$ROOT_DIR/.env.local" ]]; then
  log "Creating a local .env.local scaffold"
  cat > "$ROOT_DIR/.env.local" <<EOF
# Local runtime overrides created by install_project.sh.
# Add your real Mapbox token here before using map pages if needed.
MAPBOX_ACCESS_TOKEN=
MAPBOX_STYLE_URL=mapbox://styles/mapbox/light-v11
REDIS_HOST=127.0.0.1
REDIS_PORT=${REDIS_PORT}
REDIS_DB_OBJECTS=10
REDIS_DB_USERS=12
FLASK_PORT=8080
EOF
fi

log "Ensuring the Redis Docker image is available"
if ! docker image inspect "$REDIS_IMAGE" >/dev/null 2>&1; then
  docker pull "$REDIS_IMAGE"
fi

if [[ "$START_REDIS" == "true" ]]; then
  if docker ps --filter "name=${CONTAINER_NAME}" --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    log "Redis container already running: $CONTAINER_NAME"
  else
    log "Starting local Redis from the canonical dump"
    DETACH=true REDIS_PORT="$REDIS_PORT" CONTAINER_NAME="$CONTAINER_NAME" REDIS_IMAGE="$REDIS_IMAGE" \
      "$ROOT_DIR/run_local_redis_from_dump.sh" "$DUMP_PATH"
  fi
fi

if ! command -v pdftoppm >/dev/null 2>&1; then
  printf '\n[WARNING] %s\n' "pdftoppm was not found. data_pipeline/harvest/harvest_benedetti_media.py needs Poppler to convert PDFs via pdf2image."
fi

log "Installation completed"
cat <<EOF

Virtual environment:
  source "$VENV_DIR/bin/activate"

Standard local startup:
  ./start_local_stack.sh

Direct Flask-only startup:
  ./start_services.sh

Admin Redis page:
  https://localhost:8080/admin/redis

Notes:
  - If .env.local was created for the first time, add your Mapbox token before using map pages.
  - Redis is expected on 127.0.0.1:${REDIS_PORT}.
EOF
