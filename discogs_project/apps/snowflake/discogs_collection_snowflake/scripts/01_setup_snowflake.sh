#!/usr/bin/env bash
set -euo pipefail

# Requires: snow CLI (https://docs.snowflake.com/en/developer-guide/snowflake-cli)
# Usage: ./scripts/01_setup_snowflake.sh

SQL_FILE="$(cd "$(dirname "$0")"/.. && pwd)/setup.sql"

if command -v snow >/dev/null 2>&1; then
  echo "Running setup.sql via snow CLI..."
  snow sql -q "$(cat "$SQL_FILE")" | cat
elif command -v snowsql >/dev/null 2>&1; then
  echo "Running setup.sql via snowsql..."
  snowsql -q "$(cat "$SQL_FILE")" | cat
else
  echo "Neither 'snow' nor 'snowsql' found. Please install one of them."
  exit 1
fi

echo "Snowflake setup complete."
