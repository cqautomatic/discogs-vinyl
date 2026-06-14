#!/usr/bin/env python3
"""
Backfill missing release details (country, rating) from Discogs API.

Fetches /releases/{id} for each release missing country data and updates
the releases table. One API call per release.

Usage:
    python scripts/backfill_release_details.py
    python scripts/backfill_release_details.py --batch 100
"""

import os
import sys
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.discogs_api import DiscogsClient

_client = DiscogsClient()


def get_db():
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', '5432')),
        database=os.getenv('PGDATABASE', 'discogs_collection'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres'),
    )


def backfill(batch_limit=None):
    conn = get_db()
    conn.autocommit = False

    try:
        cur = conn.cursor()
        cur.execute("SET search_path TO collection_data, public")

        sql = """
            SELECT release_id, discogs_id
            FROM releases
            WHERE discogs_id IS NOT NULL
              AND (country IS NULL OR country = '')
            ORDER BY release_id
        """
        if batch_limit:
            sql += " LIMIT %s"
            cur.execute(sql, (batch_limit,))
        else:
            cur.execute(sql)

        rows = cur.fetchall()
        total = len(rows)
        print(f"Found {total} releases needing detail backfill")

        updated = 0
        skipped = 0

        for i, (release_id, discogs_id) in enumerate(rows, 1):
            data = _client.release(discogs_id)
            if not data:
                print(f"  [{i}/{total}] {release_id} — API returned nothing")
                skipped += 1
                continue

            country = data.get("country")
            community = data.get("community", {})
            rating = community.get("rating", {})
            avg_rating = rating.get("average")
            rating_count = rating.get("count")

            cur.execute(
                """UPDATE releases
                   SET country = COALESCE(%s, country),
                       community_average_rating = COALESCE(%s, community_average_rating),
                       community_rating_count = COALESCE(%s, community_rating_count)
                   WHERE release_id = %s""",
                (country, avg_rating, rating_count, release_id),
            )
            conn.commit()
            updated += 1
            print(f"  [{i}/{total}] {release_id} — {country or 'no country'}, rating: {avg_rating}")

        print(f"\nDone: {updated} updated, {skipped} skipped")

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill release details from Discogs API")
    parser.add_argument("--batch", type=int, default=None, help="Max releases to process")
    args = parser.parse_args()

    backfill(args.batch)
