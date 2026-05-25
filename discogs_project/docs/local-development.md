# Local Development Guide

This guide covers running the Discogs project locally: PostgreSQL via Docker Compose,
Python ingestion, the Streamlit app, and the React + Node API stack
(`apps/react-frontend` + `apps/local-api`).

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Python 3.8+
- `psql` client (optional, for manual schema inspection)

---

## 1. Start PostgreSQL

Copy the env template and set a local password:

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD to anything (e.g. "localdev")
```

Start Postgres:

```bash
docker compose up -d postgres
```

Wait for the health check to pass:

```bash
docker compose ps
# Status should show "healthy" before continuing
```

The database `discogs_collection` is created automatically with the user and password
from your `.env`. Data persists in a named Docker volume (`postgres_data`) across restarts.

To stop (data retained):

```bash
docker compose down
```

To wipe all data and start fresh:

```bash
docker compose down -v
```

---

## 2. Bootstrap the Database Schema (Safe Migrations)

The recommended bootstrap path is the migration runner — it is idempotent and safe to
run on both empty and existing databases.

### 2a. Run migrations

```bash
cd apps/local-api
npm install          # first time only
npm run migrate
```

The runner:
1. Creates the `collection_data` schema and a `schema_migrations` tracking table
2. Applies any migration files in `db/migrations/` that haven't been applied yet
3. Logs `[APPLY]` or `[SKIP]` for each file — safe to run multiple times

Set the same POSTGRES_* environment variables used by the API:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=discogs_user
export POSTGRES_PASSWORD=localdev   # match your .env
export POSTGRES_DATABASE=discogs_collection
```

Or source your `.env` file:
```bash
set -a && source .env && set +a
cd apps/local-api && npm run migrate
```

After migration, verify:
```bash
psql "postgresql://discogs_user:localdev@localhost:5432/discogs_collection" \
  -c "\dt collection_data.*"
```

### 2b. Emergency reset (destructive)

> **WARNING: This DROPS all data.** Only use on a local throwaway database you are
> willing to wipe completely. Never run against staging or production.

```bash
psql "postgresql://discogs_user:localdev@localhost:5432/discogs_collection" \
  -f apps/postgres/discogs_collection_postgres_lab/Database/setup.sql
```

---

## 3. Python Ingestion

All ingestion code lives under `apps/postgres/discogs_collection_postgres_lab/`.

### 3a. Set up a virtual environment

Using `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/postgres/discogs_collection_postgres_lab/Configuration/requirements.txt
```

Or using `uv` (faster):

```bash
uv venv
source .venv/bin/activate
uv pip install -r apps/postgres/discogs_collection_postgres_lab/Configuration/requirements.txt
```

### 3b. Configure credentials

The Python code loads config in this order (highest to lowest priority):
1. `.streamlit/secrets.toml` (Streamlit native, uses `[discogs]` and `[postgres]` sections)
2. `discogs_config.json` in the app directory
3. Environment variables (`DISCOGS_TOKEN`, `POSTGRES_*`, etc.)

The simplest local path is environment variables. Source your `.env` file:

```bash
set -a && source .env && set +a
```

Or export individually:

```bash
export DISCOGS_TOKEN=your_token_here
export DISCOGS_USERNAME=your_username
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=discogs_user
export POSTGRES_PASSWORD=localdev
export POSTGRES_DATABASE=discogs_collection
export POSTGRES_SCHEMA=collection_data
```

### 3c. Run the downloader

```bash
cd apps/postgres/discogs_collection_postgres_lab

# Dry run / small sample (first 20 releases, no artwork):
python discogs_downloader.py --max-releases 20 --no-artwork

# Full collection download (can take a while depending on collection size):
python discogs_downloader.py

# Skip artwork to speed things up:
python discogs_downloader.py --no-artwork
```

---

## 4. Streamlit App

With Postgres running and data loaded:

```bash
cd apps/postgres/discogs_collection_postgres_lab
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

The app reads DB credentials from `.streamlit/secrets.toml` first, then falls back to
environment variables. If you're using the env-var path, make sure they're exported in
the same shell where you run Streamlit.

**Known issue:** `database.py` builds the `SET search_path` string via f-string
interpolation rather than a parameterized call. This is safe for the controlled local
schema name `collection_data` but should be fixed before any user-supplied input can
reach it.

---

## 5. Python Module Verification (no runtime deps required)

Check that all Python source compiles cleanly without installing anything:

```bash
python3 -m compileall apps/postgres/discogs_collection_postgres_lab -q
```

---

## 6. React + Node API

A clean local frontend stack is available in addition to the Streamlit app:

- `apps/local-api/` — Fastify (TypeScript) service over `pg`, exposing:
  `/health`, `/api/stats`, `/api/releases`, `/api/releases/:id`, `/api/genres`,
  `/api/styles`, `/api/search`
- `apps/react-frontend/` — Vite + React + TypeScript, consuming only the local API

### 6a. Install dependencies

```bash
cd apps/local-api && npm install && cd ../..
cd apps/react-frontend && npm install && cd ../..
```

### 6b. Configure the Node API

```bash
cp apps/local-api/.env.example apps/local-api/.env
# Edit apps/local-api/.env — set POSTGRES_PASSWORD to match your root .env
```

### 6c. Start the full stack

In separate terminals (or use a process manager):

```bash
# Bootstrap schema (first time, or after wiping the volume):
cd apps/local-api && npm run migrate && cd ../..

docker compose up -d postgres          # Postgres on :5432
cd apps/local-api && npm run dev       # Node API on :3001
cd apps/react-frontend && npm run dev  # React on :5173
```

Open `http://localhost:5173`.

The Vite dev server proxies `/api` and `/health` to the Node API, so no CORS
configuration is needed beyond what is already in place.

---

## 7. Command Center & Discover Views

The React frontend includes two additional views beyond the basic browse/search:

### Command Center (tab: "Command Center")

Provides operational insight into your collection:
- **Wantlist** — your full Discogs wantlist with current pricing and availability
- **High Demand** — releases in your collection with the highest community want/have ratio
- **Budget Buys** — wantlist items available now under a price threshold you set

### Discover (tab: "Discover")

Buying guide and collection gap analysis:
- **Similar Artists** — artists in your wantlist who share labels/genres with your collection but aren't yet owned
- **Affordable Grails** — highly coveted items (high want/have ratio) that are currently cheap
- **Complete the Decade** — targeted picks from your wantlist to fill your two sparsest decades
- **Genre Value Map** — average price vs average rating per genre across your wantlist — find high-quality, low-cost genres to buy into
- **Label Gaps** — labels you collect most, sorted by average rating
- **Decade Gaps** — decade-by-decade coverage of your collection
- **Artist Gaps** — artists with the fewest owned releases (potential incomplete discographies)

The Collection Health card at the top of Discover shows a live summary:
total wantlist size, how many items are available right now, estimated total cost
to buy everything available, and items under $20.

---

## 8. Smoke Tests

Two smoke tests are available:

### Module smoke test (offline, no server required)

Verifies all route module files can be imported and export a valid plugin function:
```bash
cd apps/local-api && npm run smoke
```

### Live HTTP smoke test (requires running API)

Hits every API endpoint and validates the response shape:
```bash
cd apps/local-api && npm run smoke:http
```

To test against a non-default URL:
```bash
API_BASE=http://localhost:3001 npm run smoke:http
```

Exits 0 if all checks pass, 1 if any endpoint is unreachable or returns unexpected data.

---

## Troubleshooting

**`POSTGRES_PASSWORD must be set in .env`**
You ran `docker compose up` without a `.env` file. Copy `.env.example` to `.env` and set the password.

**`psycopg2.OperationalError: Connection refused`**
Postgres container is not running or not yet healthy. Run `docker compose ps` and wait
for the health check to show `healthy`.

**Streamlit shows "Database connection failed"**
Credentials are not in scope. Verify env vars are exported (`echo $POSTGRES_HOST`)
or create `.streamlit/secrets.toml`:
```toml
[discogs]
token = "your_token"
username = "your_username"

[postgres]
host = "localhost"
port = 5432
user = "discogs_user"
password = "localdev"
database = "discogs_collection"
schema = "collection_data"
```
`.streamlit/secrets.toml` is in `.gitignore` — never commit it.

**Schema missing after restarting Postgres**
The schema is created by the migration runner, not by the Docker image. If you ran
`docker compose down -v`, the volume was wiped. Re-run step 2 (`npm run migrate`).
