#!/usr/bin/env python3
"""
Fetch artwork URLs from Discogs API and store them in the releases table.

This is a lightweight alternative to the full discogs_downloader — it only
fetches image URLs (one API call per release) and updates artwork_urls in
the DB so that enhanced_artwork_downloader.py can download the actual files.

Usage:
    python scripts/fetch_artwork_urls.py                # all releases missing artwork_urls
    python scripts/fetch_artwork_urls.py --batch 100    # limit to 100 releases
"""

import os
import sys
import json
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


def fetch_artwork_urls(batch_limit=None):
    conn = get_db()
    conn.autocommit = False

    try:
        cur = conn.cursor()
        cur.execute("SET search_path TO collection_data, public")

        # Find releases that have a discogs_id but no artwork_urls yet
        sql = """
            SELECT release_id, discogs_id
            FROM releases
            WHERE discogs_id IS NOT NULL
              AND (artwork_urls IS NULL OR artwork_urls = '[]'::jsonb)
            ORDER BY release_id
        """
        if batch_limit:
            sql += " LIMIT %s"
            cur.execute(sql, (batch_limit,))
        else:
            cur.execute(sql)

        rows = cur.fetchall()
        total = len(rows)
        print(f"Found {total} releases needing artwork URLs")

        updated = 0
        skipped = 0

        for i, (release_id, discogs_id) in enumerate(rows, 1):
            data = _client.release(discogs_id)
            if not data:
                print(f"  [{i}/{total}] {release_id} (discogs:{discogs_id}) — API returned nothing, skipping")
                skipped += 1
                continue

            images = data.get("images", [])
            if not images:
                print(f"  [{i}/{total}] {release_id} — no images on Discogs")
                skipped += 1
                continue

            # Extract URLs, preferring resource_url (full-size) over uri/uri150
            urls = [img.get("resource_url") or img.get("uri") for img in images if img.get("resource_url") or img.get("uri")]

            cur.execute(
                "UPDATE releases SET artwork_urls = %s WHERE release_id = %s",
                (json.dumps(urls), release_id),
            )
            conn.commit()
            updated += 1
            print(f"  [{i}/{total}] {release_id} — {len(urls)} image(s)")

        print(f"\nDone: {updated} updated, {skipped} skipped")

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch artwork URLs from Discogs API")
    parser.add_argument("--batch", type=int, default=None, help="Max releases to process")
    args = parser.parse_args()

    fetch_artwork_urls(args.batch)
