#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://github.com/astral-sh/uv" >&2
  exit 1
fi

uv sync --extra docs
uv run zensical serve --config-file mkdocs.yml
