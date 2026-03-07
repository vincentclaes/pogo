#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

API_HOST="${POGO_API_HOST:-127.0.0.1}"
API_PORT="${POGO_API_PORT:-8000}"
WEB_PORT="${POGO_WEB_PORT:-3000}"

export NEXT_PUBLIC_API_BASE="${NEXT_PUBLIC_API_BASE:-http://${API_HOST}:${API_PORT}}"

BACKEND_CMD=${POGO_BACKEND_CMD:-"uv run uvicorn pogo.api.app:app --reload --host ${API_HOST} --port ${API_PORT}"}
FRONTEND_CMD=${POGO_FRONTEND_CMD:-"npm run dev -- --port ${WEB_PORT}"}

cleanup() {
  echo "\nStopping processes..."
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting backend: ${BACKEND_CMD}"
(
  cd "$BACKEND_DIR"
  eval "$BACKEND_CMD"
) &
BACKEND_PID=$!

echo "Starting frontend: ${FRONTEND_CMD}"
(
  cd "$FRONTEND_DIR"
  eval "$FRONTEND_CMD"
) &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://${API_HOST}:${API_PORT}"
echo "Frontend: http://localhost:${WEB_PORT}"
echo "API base: ${NEXT_PUBLIC_API_BASE}"

echo "\nPress Ctrl+C to stop."

wait "$BACKEND_PID" "$FRONTEND_PID"
