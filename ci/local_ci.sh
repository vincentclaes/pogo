#!/usr/bin/env bash
set -euo pipefail

echo "[local-ci] syncing dependencies"
uv sync --dev

echo "[local-ci] lint (ruff)"
uv run ruff check .

echo "[local-ci] type check (ty)"
uv run ty check

echo "[local-ci] security (bandit)"
uv run bandit -q -r app biosignal

echo "[local-ci] dependency audit (pip-audit)"
uv run pip-audit

echo "[local-ci] tests"
uv run pytest

echo "[local-ci] done"
