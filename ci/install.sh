#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "Backend directory not found: $BACKEND_DIR" >&2
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "Frontend directory not found: $FRONTEND_DIR" >&2
  exit 1
fi

echo "[install] backend dependencies"
(
  cd "$BACKEND_DIR"
  if [[ -x "ci/setup.sh" ]]; then
    ./ci/setup.sh
  else
    echo "Missing backend/ci/setup.sh" >&2
    exit 1
  fi
)

echo "[install] frontend dependencies"
(
  cd "$FRONTEND_DIR"
  npm install
)

echo "[install] done"
