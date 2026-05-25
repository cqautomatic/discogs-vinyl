# Discogs Collection — Snowflake (SiS)

A Snowflake-native port of the PostgreSQL app using Streamlit-in-Snowflake (SiS) and Snowpark, mirroring all major enhancements (community stats, genre/style views, decade analysis, browse).

## Step-by-step (scripts provided)

- 01) Bootstrap Snowflake (roles, DB, schema, tables)
  - Script: `discogs_collection_snowflake/scripts/01_setup_snowflake.sh`
  - Runs the `setup.sql` file using Snow CLI (or Snowsql if preferred)

- 02) Ingest sample data (full run)
  - Script: `discogs_collection_snowflake/scripts/02_full_run.sh`
  - Uses `snowflake_downloader.py --full-run` with your env vars

- 03) Refresh a single release stats
  - Script: `discogs_collection_snowflake/scripts/03_refresh_release.sh <discogs_release_id>`

- 04) Run the Streamlit UI locally (for quick validation)
  - Script: `discogs_collection_snowflake/scripts/04_run_streamlit_local.sh`

- 05) Run tests
  - Script: `discogs_collection_snowflake/scripts/05_run_tests.sh`

## Prerequisites

- Snowflake CLI (`snow`) or Snowsql (`snowsql`)
- Python 3.10+
- Environment variables set for Snowflake and Discogs:
  - `SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA`
  - `DISCOGS_TOKEN, DISCOGS_USER_AGENT`

## Files

- `setup.sql` — Creates roles, warehouse, database, schema, stages, and tables
- `snowflake_downloader.py` — Snowpark-based downloader/ingestor
- `streamlit_app_sis.py` — Streamlit UI for SiS
- `requirements.txt` — Python deps for local runs
- `scripts/` — Step-by-step automation scripts
