# Discogs PostgreSQL App

Streamlit app and ingestion for Discogs collections on PostgreSQL.

## Setup
- Create `.streamlit/secrets.toml` with `[discogs]` and `[postgres]` sections.
- Run initial schema: `setup.sql` (under app directory)

## Launch
```
streamlit run streamlit_app.py
```

## Refresh Stats
```
python discogs_downloader.py --refresh-stats
```

## Full Run
```
python discogs_downloader.py --full-run
```
