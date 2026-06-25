#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT_DIR/nanobot/.venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "Missing nanobot virtual environment: $VENV_PY" >&2
  echo "Run: cd \"$ROOT_DIR/nanobot\" && python3 -m venv .venv && .venv/bin/python -m pip install -e . && .venv/bin/python -m pip install -r ../demo/requirements.txt" >&2
  exit 1
fi

cd "$ROOT_DIR"
if [ -f "$ROOT_DIR/demo/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/demo/.env.local"
  set +a
fi

UVICORN_ARGS=(
  demo.backend.app:app
  --host "${TABLEAGENT_DEMO_HOST:-127.0.0.1}"
  --port "${TABLEAGENT_DEMO_PORT:-8787}"
)

if [ "${TABLEAGENT_DEMO_RELOAD:-0}" = "1" ]; then
  UVICORN_ARGS+=(--reload --reload-dir "$ROOT_DIR/demo/backend")
fi

exec "$VENV_PY" -m uvicorn "${UVICORN_ARGS[@]}"
