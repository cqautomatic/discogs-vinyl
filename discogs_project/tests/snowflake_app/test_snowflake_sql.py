import re
from pathlib import Path

# Updated path after repo reorganization
SQL_PATH = Path('discogs_project/apps/snowflake/discogs_collection_snowflake/setup.sql')


def test_setup_sql_exists():
    assert SQL_PATH.exists()


def test_setup_sql_contains_core_objects():
    text = SQL_PATH.read_text()
    # Core roles
    assert 'CREATE ROLE IF NOT EXISTS DISCOGS_ADMIN_ROLE' in text
    assert 'CREATE ROLE IF NOT EXISTS DISCOGS_READER_ROLE' in text
    # Core database/schema
    assert 'CREATE DATABASE IF NOT EXISTS DISCOGS_DB' in text
    assert 'CREATE SCHEMA IF NOT EXISTS DISCOGS_DB.COLLECTION_DATA' in text
    # Core tables
    assert 'CREATE TABLE IF NOT EXISTS DISCOGS_DB.COLLECTION_DATA.RELEASES' in text
    assert 'CREATE TABLE IF NOT EXISTS DISCOGS_DB.COLLECTION_DATA.ARTWORK' in text
    assert 'CREATE TABLE IF NOT EXISTS DISCOGS_DB.COLLECTION_DATA.MARKETPLACE_STATS_DIM' in text
    assert 'CREATE TABLE IF NOT EXISTS DISCOGS_DB.COLLECTION_DATA.RELEASE_PRICES' in text
