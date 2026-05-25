#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/03_refresh_release.sh <discogs_release_id>

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <discogs_release_id>"
  exit 1
fi

RID="$1"
PY="$(command -v python || command -v python3)"
APP="$(cd "$(dirname "$0")"/.. && pwd)/snowflake_downloader.py"

exec "$PY" "$APP" --refresh-release-stats "$RID"
