"""
sync_new_releases.py — Fetch new releases for top artists and store in new_releases_feed.

Usage:
    python sync_new_releases.py
"""

import os
import time
import json
from urllib.parse import quote

import requests
import psycopg2

DISCOGS_TOKEN = os.environ["DISCOGS_TOKEN"]
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "discogs_user")
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "discogs_collection")

HEADERS = {
    "Authorization": f"Discogs token={DISCOGS_TOKEN}",
    "User-Agent": "DiscogsCollectionApp/1.0",
}


def main():
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DATABASE,
    )
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")

        # Top 20 artists by release count
        cur.execute(
            """
            SELECT artist, COUNT(*) AS cnt
            FROM releases
            WHERE artist IS NOT NULL
            GROUP BY artist
            ORDER BY cnt DESC
            LIMIT 20
            """
        )
        top_artists = [row[0] for row in cur.fetchall()]

        # Set of already-owned discogs IDs
        cur.execute("SELECT discogs_id FROM releases WHERE discogs_id IS NOT NULL")
        owned_ids = {row[0] for row in cur.fetchall()}

    inserted = 0
    skipped = 0

    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")

        for artist in top_artists:
            url = (
                f"https://api.discogs.com/database/search"
                f"?artist={quote(artist)}&type=release&sort=year&sort_order=desc&per_page=10"
            )
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.exceptions.RequestException as exc:
                print(f"Request failed for artist '{artist}': {exc}")
                time.sleep(1.0)
                continue

            for result in data.get("results", []):
                release_id = result.get("id")
                if release_id is None or release_id in owned_ids:
                    skipped += 1
                    continue

                raw_title = result.get("title", "")
                parts = raw_title.split(" - ", 1)
                if len(parts) == 2:
                    result_artist, title = parts[0], parts[1]
                else:
                    result_artist, title = artist, raw_title

                year_raw = result.get("year")
                try:
                    year = int(year_raw) if year_raw else None
                except (ValueError, TypeError):
                    year = None

                label = (result.get("label") or [None])[0]
                fmt = (result.get("format") or [None])[0]
                genres = json.dumps(result.get("genre", []))
                country = result.get("country")

                cur.execute(
                    """
                    INSERT INTO new_releases_feed
                        (discogs_release_id, title, artist, year, label, format, genres, country)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (discogs_release_id) DO NOTHING
                    """,
                    (release_id, title, result_artist, year, label, fmt, genres, country),
                )
                if cur.rowcount:
                    inserted += 1
                else:
                    skipped += 1

            time.sleep(1.0)

    conn.close()
    print(
        f"Sync complete: {inserted} new releases added, "
        f"{skipped} skipped (owned or duplicate)"
    )


if __name__ == "__main__":
    main()
