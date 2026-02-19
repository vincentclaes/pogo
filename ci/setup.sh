#!/usr/bin/env bash
set -euo pipefail

echo "[setup] installing dependencies"
uv sync --dev

echo "[setup] done"
