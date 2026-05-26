"""
sync_new_releases.py — Discover releases you don't own yet, based on your
top labels, top genres/styles, and related artists. Stores results in
new_releases_feed so the React UI can display them.

Usage:
    python sync_new_releases.py
"""

import os
import time
import json
from urllib.parse import quote

import requests
import psycopg2

DISCOGS_TOKEN    = os.environ["DISCOGS_TOKEN"]
POSTGRES_HOST    = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT    = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER    = os.getenv("POSTGRES_USER", "discogs_user")
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "discogs_collection")

HEADERS = {
    "Authorization": f"Discogs token={DISCOGS_TOKEN}",
    "User-Agent": "DiscogsCollectionApp/1.0",
}

RATE_DELAY = 1.1   # seconds between API calls


def search_discogs(params: dict) -> list:
    url = "https://api.discogs.com/database/search"
    try:
        resp = requests.get(url, headers=HEADERS, params={**params, "per_page": 20, "type": "release"}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.RequestException as exc:
        print(f"  API error: {exc}")
        return []
    finally:
        time.sleep(RATE_DELAY)


def insert_result(cur, result: dict, owned_ids: set, source: str) -> tuple[int, int]:
    release_id = result.get("id")
    if not release_id or release_id in owned_ids:
        return 0, 1

    raw_title = result.get("title", "")
    parts = raw_title.split(" - ", 1)
    artist = parts[0] if len(parts) == 2 else ""
    title  = parts[1] if len(parts) == 2 else raw_title

    try:
        year = int(result["year"]) if result.get("year") else None
    except (ValueError, TypeError):
        year = None

    label   = (result.get("label") or [None])[0]
    fmt     = (result.get("format") or [None])[0]
    genres  = json.dumps(result.get("genre", []))
    country = result.get("country")

    cur.execute(
        """
        INSERT INTO new_releases_feed
            (discogs_release_id, title, artist, year, label, format, genres, country, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (discogs_release_id) DO NOTHING
        """,
        (release_id, title, artist, year, label, fmt, genres, country, source),
    )
    return (1, 0) if cur.rowcount else (0, 1)


def main():
    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        database=POSTGRES_DATABASE,
    )
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")

        # IDs you already own
        cur.execute("SELECT discogs_id FROM releases WHERE discogs_id IS NOT NULL")
        owned_ids = {row[0] for row in cur.fetchall()}

        # Top 10 labels by ownership count
        cur.execute("""
            SELECT label, COUNT(*) AS cnt
            FROM releases
            WHERE label IS NOT NULL AND label != ''
            GROUP BY label ORDER BY cnt DESC LIMIT 10
        """)
        top_labels = [r[0] for r in cur.fetchall()]

        # Top 5 genres
        cur.execute("""
            SELECT genre_val, COUNT(*) AS cnt
            FROM releases, jsonb_array_elements_text(COALESCE(genres,'[]'::jsonb)) AS genre_val
            GROUP BY genre_val ORDER BY cnt DESC LIMIT 5
        """)
        top_genres = [r[0] for r in cur.fetchall()]

        # Top 15 artists by count (for related search)
        cur.execute("""
            SELECT artist, COUNT(*) AS cnt
            FROM releases WHERE artist IS NOT NULL
            GROUP BY artist ORDER BY cnt DESC LIMIT 15
        """)
        top_artists = [r[0] for r in cur.fetchall()]

    inserted = skipped = 0

    print(f"Searching by {len(top_labels)} labels, {len(top_genres)} genres, {len(top_artists)} artists...")

    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")

        # 1. Search by top labels — finds new releases on labels you already buy
        for label in top_labels:
            print(f"  label: {label}")
            results = search_discogs({"label": label, "sort": "year", "sort_order": "desc"})
            for r in results:
                i, s = insert_result(cur, r, owned_ids, f"label:{label}")
                inserted += i; skipped += s

        # 2. Search by top genres — broad discovery
        for genre in top_genres:
            print(f"  genre: {genre}")
            results = search_discogs({"genre": genre, "sort": "have", "sort_order": "desc"})
            for r in results:
                i, s = insert_result(cur, r, owned_ids, f"genre:{genre}")
                inserted += i; skipped += s

        # 3. Search by top artists — catches releases you're missing
        for artist in top_artists:
            print(f"  artist: {artist}")
            results = search_discogs({"artist": quote(artist), "sort": "year", "sort_order": "desc"})
            for r in results:
                i, s = insert_result(cur, r, owned_ids, f"artist:{artist}")
                inserted += i; skipped += s

    conn.close()
    print(f"Sync complete: {inserted} new releases added, {skipped} skipped (owned or duplicate)")


if __name__ == "__main__":
    main()
