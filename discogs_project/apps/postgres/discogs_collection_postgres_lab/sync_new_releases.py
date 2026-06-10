"""
sync_new_releases.py — Discover releases you don't own yet, based on your
top labels, top genres/styles, and related artists. Stores results in
new_releases_feed so the React UI can display them.

Usage:
    python sync_new_releases.py
"""

import os
import json
import time
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

# Load discovery styles from the shared config (single source of truth)
_STYLES_CONFIG = os.path.join(os.path.dirname(__file__), "../../../config/discovery-styles.json")
with open(os.path.normpath(_STYLES_CONFIG)) as _f:
    DISCOVERY_STYLES: list[str] = json.load(_f)["styles"]

# Lowercase set for fast membership checks in insert_result
WANTED_STYLES = {s.lower() for s in DISCOVERY_STYLES}


def search_discogs(params: dict) -> list:
    url = "https://api.discogs.com/database/search"
    try:
        resp = requests.get(
            url, headers=HEADERS,
            params={**params, "per_page": 25, "type": "release", "format": "Vinyl"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.RequestException as exc:
        print(f"  API error: {exc}")
        return []
    finally:
        time.sleep(RATE_DELAY)


def insert_result(cur, result: dict, owned_ids: set, owned_master_ids: set, source: str, bypass_genre_filter: bool = False) -> tuple[int, int]:
    release_id = result.get("id")
    if not release_id or release_id in owned_ids:
        return 0, 1

    # Skip if you own any other pressing of the same album
    master_id = result.get("master_id") or result.get("master") or None
    if master_id:
        try:
            master_id = int(master_id)
        except (ValueError, TypeError):
            master_id = None
    if master_id and master_id in owned_master_ids:
        return 0, 1

    # Skip non-vinyl formats
    formats = [f.lower() for f in (result.get("format") or [])]
    if formats and not any("vinyl" in f or '12"' in f or '7"' in f or '10"' in f or "lp" in f for f in formats):
        return 0, 1

    # Genre/style filter — bypass when searching by a curated style (already on-target)
    if not bypass_genre_filter:
        WANTED_GENRES = {"electronic", "funk / soul", "funk/soul", "jazz", "hip hop", "reggae", "latin", "soul", "pop"}
        result_genres = {g.lower() for g in (result.get("genre") or [])}
        result_styles = {s.lower() for s in (result.get("style") or [])}
        genre_ok = not result_genres or result_genres.intersection(WANTED_GENRES)
        style_ok = result_styles.intersection(WANTED_STYLES)
        if not genre_ok and not style_ok:
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
    styles  = json.dumps(result.get("style", []))
    country = result.get("country")
    thumb   = result.get("cover_image") or result.get("thumb")

    cur.execute(
        """
        INSERT INTO new_releases_feed
            (discogs_release_id, master_id, title, artist, year, label, format, genres, styles, country, source, thumb)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (discogs_release_id) DO UPDATE SET
          master_id = COALESCE(new_releases_feed.master_id, EXCLUDED.master_id),
          thumb     = COALESCE(new_releases_feed.thumb,     EXCLUDED.thumb),
          styles    = COALESCE(new_releases_feed.styles,    EXCLUDED.styles),
          genres    = COALESCE(new_releases_feed.genres,    EXCLUDED.genres)
        RETURNING (xmax = 0) AS inserted
        """,
        (release_id, master_id, title, artist, year, label, fmt, genres, styles, country, source, thumb),
    )
    # xmax = 0 only for genuine inserts; conflict-updates report it non-zero
    row = cur.fetchone()
    return (1, 0) if row and row[0] else (0, 1)


def main():
    conn = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        database=POSTGRES_DATABASE,
    )
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")

        # Exact release IDs you already own
        cur.execute("SELECT discogs_id FROM releases WHERE discogs_id IS NOT NULL")
        owned_ids = {row[0] for row in cur.fetchall()}

        # master_ids you already own (catches reissues / alternate pressings)
        cur.execute("""
            SELECT DISTINCT (basic_information->>'master_id')::int
            FROM releases
            WHERE basic_information->>'master_id' IS NOT NULL
        """)
        owned_master_ids = {row[0] for row in cur.fetchall()}

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

        # Top 15 artists by count (for related search) — exclude compilations
        cur.execute("""
            SELECT artist, COUNT(*) AS cnt
            FROM releases WHERE artist IS NOT NULL AND artist NOT ILIKE '%various%'
            GROUP BY artist ORDER BY cnt DESC LIMIT 15
        """)
        top_artists = [r[0] for r in cur.fetchall()]

    inserted = skipped = 0
    style_counts: dict[str, int] = {}

    print(f"Searching by {len(top_labels)} labels, {len(top_genres)} genres, "
          f"{len(top_artists)} artists, {len(DISCOVERY_STYLES)} curated styles...")

    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")

        # 1. Search by top labels
        for label in top_labels:
            print(f"  label: {label}")
            results = search_discogs({"label": label, "sort": "year", "sort_order": "desc"})
            for r in results:
                i, s = insert_result(cur, r, owned_ids, owned_master_ids, f"label:{label}")
                inserted += i; skipped += s

        # 2. Search by top genres — broad discovery
        for genre in top_genres:
            print(f"  genre: {genre}")
            results = search_discogs({"genre": genre, "sort": "have", "sort_order": "desc"})
            for r in results:
                i, s = insert_result(cur, r, owned_ids, owned_master_ids, f"genre:{genre}")
                inserted += i; skipped += s

        # 3. Search by top artists — catches releases you're missing
        for artist in top_artists:
            print(f"  artist: {artist}")
            results = search_discogs({"artist": quote(artist), "sort": "year", "sort_order": "desc"})
            for r in results:
                i, s = insert_result(cur, r, owned_ids, owned_master_ids, f"artist:{artist}")
                inserted += i; skipped += s

        # 4. Search by curated discovery styles (from config/discovery-styles.json)
        #    bypass_genre_filter=True because these are exactly on-target
        for style in DISCOVERY_STYLES:
            print(f"  style: {style}")
            results = search_discogs({"style": style, "sort": "have", "sort_order": "desc"})
            style_n = 0
            for r in results:
                i, s = insert_result(cur, r, owned_ids, owned_master_ids, f"style:{style}", bypass_genre_filter=True)
                inserted += i; skipped += s
                style_n += i
            style_counts[style] = style_n

    conn.close()

    print("\nPer-style inserts:")
    for style, count in style_counts.items():
        print(f"  {style}: {count}")
    print(f"\nSync complete: {inserted} new releases added, {skipped} skipped (owned or duplicate)")


if __name__ == "__main__":
    main()
