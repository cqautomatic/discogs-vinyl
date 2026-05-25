import os
import sys
from pathlib import Path

# Ensure Discogs Postgres app and scripts are on PYTHONPATH for tests
# ROOT should be the discogs_project directory
ROOT = Path(__file__).resolve().parents[1]
POSTGRES_APP = ROOT / 'apps' / 'postgres' / 'discogs_collection_postgres_lab'
SCRIPTS_DIR = ROOT / 'scripts'

for p in (POSTGRES_APP, SCRIPTS_DIR):
    p_str = str(p)
    if p_str not in sys.path and p.exists():
        sys.path.append(p_str)


