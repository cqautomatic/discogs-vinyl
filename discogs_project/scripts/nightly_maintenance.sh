#!/bin/bash

# Nightly Discogs Maintenance Script
# Runs at 1 AM daily via crontab:
#   0 1 * * * /Users/joeyfoley/cursor_1/discogs_project/scripts/nightly_maintenance.sh
#
# Steps:
#   1. Incremental collection sync (new releases added in last ~30 days)
#   2. Price refresh (marketplace prices + availability)
#   3. Materialized views refresh (genre/style/decade/artwork/collection stats)

set -euo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT="/Users/joeyfoley/cursor_1/discogs_project"
VENV="$PROJECT_ROOT/.venv/bin/activate"
WORK_DIR="$PROJECT_ROOT/apps/postgres/discogs_collection_postgres_lab"
LOG_FILE="$PROJECT_ROOT/logs/nightly_maintenance.log"

mkdir -p "$(dirname "$LOG_FILE")"

# ── Environment ───────────────────────────────────────────────────────────────
# Credentials are read from .streamlit/secrets.toml by the Python scripts,
# but we also export them here for any subprocess that needs them directly.
export DISCOGS_TOKEN="MxgSiRPTvDNMHmeFSmVOzZaUfwxlQrvBJaZkwnLG"
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="discogs_collection"
export POSTGRES_USER="discogs_user"
export POSTGRES_PASSWORD="PG_jofoley927"
export PGPASSWORD="PG_jofoley927"
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# ── Activate the correct venv ─────────────────────────────────────────────────
if [[ ! -f "$VENV" ]]; then
    echo "$(date): ERROR - venv not found at $VENV" >> "$LOG_FILE"
    exit 1
fi
# shellcheck disable=SC1090
source "$VENV"

cd "$WORK_DIR"

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "$(date '+%Y-%m-%d %H:%M:%S'): $*" >> "$LOG_FILE"; }

run_step() {
    local name="$1"; shift
    log "Starting: $name"
    if "$@" >> "$LOG_FILE" 2>&1; then
        log "OK: $name"
        return 0
    else
        log "FAILED: $name (exit $?)"
        return 1
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
log "===== Nightly maintenance starting ====="
OVERALL=0

# 1. Incremental collection sync — picks up releases added in the last ~30 days
run_step "incremental collection sync" \
    python3 discogs_downloader.py --incremental-run || OVERALL=1

# 2. Price refresh — marketplace prices + availability
run_step "price refresh" \
    python3 discogs_downloader.py --refresh-prices || OVERALL=1

# 3. Materialized views — reflect the freshly synced data
run_step "materialized views refresh" \
    python3 refresh_views.py --quiet || OVERALL=1

if [[ $OVERALL -eq 0 ]]; then
    log "===== Nightly maintenance completed successfully ====="
else
    log "===== Nightly maintenance finished WITH ERRORS — check log above ====="
fi

echo "------------------------------------------------------------" >> "$LOG_FILE"
