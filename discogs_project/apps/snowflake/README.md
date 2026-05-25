# Discogs Snowflake (SiS)

Snowflake Streamlit-in-Snowflake app and Snowpark downloader mirroring the PostgreSQL features.

## Steps
1) Run setup
```
./discogs_collection_snowflake/scripts/01_setup_snowflake.sh
```
2) Full ingest (sample)
```
./discogs_collection_snowflake/scripts/02_full_run.sh
```
3) Refresh single release
```
./discogs_collection_snowflake/scripts/03_refresh_release.sh <id>
```
4) Run SiS app locally
```
./discogs_collection_snowflake/scripts/04_run_streamlit_local.sh
```
