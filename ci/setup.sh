#!/usr/bin/env bash
set -euo pipefail

echo "[setup] installing dependencies"
extras=(--extra dev)
if [[ "${WITH_DOCS:-0}" == "1" ]]; then
  extras+=(--extra docs)
fi
uv sync "${extras[@]}"

echo "[setup] done"
