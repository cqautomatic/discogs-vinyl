import os
import time
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, lit


class SnowflakeConfig:
    def __init__(self) -> None:
        self.account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.user = os.getenv('SNOWFLAKE_USER')
        self.password = os.getenv('SNOWFLAKE_PASSWORD')
        self.role = os.getenv('SNOWFLAKE_ROLE', 'DISCOGS_ADMIN_ROLE')
        self.warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'DISCOGS_WH')
        self.database = os.getenv('SNOWFLAKE_DATABASE', 'DISCOGS_DB')
        self.schema = os.getenv('SNOWFLAKE_SCHEMA', 'COLLECTION_DATA')
        self.discogs_token = os.getenv('DISCOGS_TOKEN', '')
        self.user_agent = os.getenv('DISCOGS_USER_AGENT', 'DiscogsCollectionDownloader/1.0')
        self.rate_limit_delay = float(os.getenv('DISCOGS_RATE_LIMIT_DELAY', '1.0'))

    def to_session_options(self) -> Dict[str, Any]:
        return {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "role": self.role,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
        }


def get_session(cfg: SnowflakeConfig) -> Session:
    return Session.builder.configs(cfg.to_session_options()).create()


def discogs_get(url: str, cfg: SnowflakeConfig) -> Dict[str, Any]:
    headers = {
        'Authorization': f'Discogs token={cfg.discogs_token}',
        'User-Agent': cfg.user_agent,
    }
    resp = requests.get(url, headers=headers, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Discogs API error {resp.status_code}: {resp.text}")
    return resp.json()


def upsert_release(session: Session, release: Dict[str, Any]) -> None:
    # Minimal upsert for Snowflake table structure
    # Use MERGE for idempotent upsert by DISCOGS_ID
    session.sql(
        """
        MERGE INTO DISCOGS_DB.COLLECTION_DATA.RELEASES t
        USING (
            SELECT
                :discogs_id::INTEGER AS DISCOGS_ID,
                :title::STRING AS TITLE,
                :artist::STRING AS ARTIST,
                :label::STRING AS LABEL,
                :year::INTEGER AS YEAR,
                :country::STRING AS COUNTRY,
                :genres::ARRAY AS GENRES,
                :styles::ARRAY AS STYLES,
                :copies_count::INTEGER AS COPIES_COUNT,
                :community_have::INTEGER AS COMMUNITY_HAVE_COUNT,
                :community_want::INTEGER AS COMMUNITY_WANT_COUNT,
                :comm_avg_rating::FLOAT AS COMMUNITY_AVERAGE_RATING,
                :comm_rating_count::INTEGER AS COMMUNITY_RATING_COUNT,
                :stats_updated::TIMESTAMP AS STATS_LAST_UPDATED
        ) s
        ON t.DISCOGS_ID = s.DISCOGS_ID
        WHEN MATCHED THEN UPDATE SET
            TITLE = s.TITLE,
            ARTIST = s.ARTIST,
            LABEL = s.LABEL,
            YEAR = s.YEAR,
            COUNTRY = s.COUNTRY,
            GENRES = s.GENRES,
            STYLES = s.STYLES,
            COPIES_COUNT = s.COPIES_COUNT,
            COMMUNITY_HAVE_COUNT = s.COMMUNITY_HAVE_COUNT,
            COMMUNITY_WANT_COUNT = s.COMMUNITY_WANT_COUNT,
            COMMUNITY_AVERAGE_RATING = s.COMMUNITY_AVERAGE_RATING,
            COMMUNITY_RATING_COUNT = s.COMMUNITY_RATING_COUNT,
            STATS_LAST_UPDATED = s.STATS_LAST_UPDATED
        WHEN NOT MATCHED THEN INSERT (
            DISCOGS_ID, TITLE, ARTIST, LABEL, YEAR, COUNTRY, GENRES, STYLES,
            COPIES_COUNT, COMMUNITY_HAVE_COUNT, COMMUNITY_WANT_COUNT,
            COMMUNITY_AVERAGE_RATING, COMMUNITY_RATING_COUNT, STATS_LAST_UPDATED
        ) VALUES (
            s.DISCOGS_ID, s.TITLE, s.ARTIST, s.LABEL, s.YEAR, s.COUNTRY, s.GENRES, s.STYLES,
            s.COPIES_COUNT, s.COMMUNITY_HAVE_COUNT, s.COMMUNITY_WANT_COUNT,
            s.COMMUNITY_AVERAGE_RATING, s.COMMUNITY_RATING_COUNT, s.STATS_LAST_UPDATED
        )
        """
    ).bind(
        discogs_id=release.get('id'),
        title=release.get('title'),
        artist=', '.join([a.get('name') for a in release.get('artists', [])]) if release.get('artists') else None,
        label=', '.join([l.get('name') for l in release.get('labels', [])]) if release.get('labels') else None,
        year=release.get('year'),
        country=release.get('country'),
        genres=release.get('genres') or [],
        styles=release.get('styles') or [],
        copies_count=1,
        community_have=release.get('community', {}).get('have'),
        community_want=release.get('community', {}).get('want'),
        comm_avg_rating=(release.get('community', {}).get('rating') or {}).get('average'),
        comm_rating_count=(release.get('community', {}).get('rating') or {}).get('count'),
        stats_updated=datetime.utcnow().isoformat()
    ).collect()


def fetch_release(cfg: SnowflakeConfig, release_id: int) -> Dict[str, Any]:
    url = f"https://api.discogs.com/releases/{release_id}"
    return discogs_get(url, cfg)


def refresh_release_stats(session: Session, cfg: SnowflakeConfig, release_id: int) -> None:
    data = fetch_release(cfg, release_id)
    upsert_release(session, data)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Snowflake Discogs Downloader')
    parser.add_argument('--full-run', action='store_true')
    parser.add_argument('--refresh-release-stats', type=int, default=None)
    args = parser.parse_args()

    cfg = SnowflakeConfig()
    if not cfg.discogs_token:
        raise SystemExit('DISCOGS_TOKEN is required')

    session = get_session(cfg)
    session.use_warehouse(cfg.warehouse)
    session.use_database(cfg.database)
    session.use_schema(cfg.schema)

    if args.refresh_release_stats:
        refresh_release_stats(session, cfg, args.refresh_release_stats)
        print(f"Refreshed stats for release {args.refresh_release_stats}")
        return

    if args.full_run:
        # Example: upsert a few known releases (real flows should iterate user collection via Discogs API)
        sample_ids = [249504, 249505, 249506]
        for rid in sample_ids:
            data = fetch_release(cfg, rid)
            upsert_release(session, data)
            time.sleep(cfg.rate_limit_delay)
        print('Full run completed (sample).')


if __name__ == '__main__':
    main()
