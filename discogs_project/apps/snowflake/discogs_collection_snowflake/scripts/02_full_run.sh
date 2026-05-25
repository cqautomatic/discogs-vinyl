#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/02_full_run.sh

PY="$(command -v python || command -v python3)"
APP="$(cd "$(dirname "$0")"/.. && pwd)/snowflake_downloader.py"

exec "$PY" "$APP" --full-run
