#!/usr/bin/env python3
"""Fast bulk import — uses only collection pages (1 API call per 50 releases).
Skips artist details, marketplace stats, and artwork for speed."""

import os, sys, json, psycopg2, psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.discogs_api import DiscogsClient

USERNAME = os.environ.get('DISCOGS_USERNAME', '')

def pg_connect():
    conn = psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', '127.0.0.1'),
        port=int(os.environ.get('POSTGRES_PORT', '5432')),
        user=os.environ.get('POSTGRES_USER', 'discogs_user'),
        password=os.environ['POSTGRES_PASSWORD'],
        database=os.environ.get('POSTGRES_DATABASE', 'discogs_collection'),
    )
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET search_path TO collection_data, public")
    conn.commit()
    return conn

def safe_join(items, field='name'):
    if not items: return ''
    try:
        return ', '.join(i.get(field, '') if isinstance(i, dict) else str(i) for i in items if i)
    except: return ''

def safe_list(val):
    if isinstance(val, list): return val
    if isinstance(val, str): return [val] if val else []
    return []

def main():
    client = DiscogsClient()
    identity = client.identity()
    if not identity:
        print("Failed to authenticate with Discogs API")
        sys.exit(1)
    username = USERNAME or identity['username']
    user_id = identity['id']

    conn = pg_connect()
    collection_id = f"collection_{user_id}"

    # Upsert collection record
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO collections (collection_id, user_id, username, collection_name, total_items)
            VALUES (%s, %s, %s, %s, 0)
            ON CONFLICT (collection_id) DO UPDATE SET username = EXCLUDED.username, last_updated = NOW()
        """, (collection_id, user_id, username, f"{username}'s Collection"))
    conn.commit()

    page = 1
    total = 0
    imported = 0

    while True:
        print(f"Fetching page {page}...")
        data = client.collection_page(username, page=page)
        if not data:
            print("Failed to fetch collection page")
            break

        if page == 1:
            total = data['pagination']['items']
            print(f"Collection has {total} items")
            with conn.cursor() as cur:
                cur.execute("UPDATE collections SET total_items = %s WHERE collection_id = %s", (total, collection_id))
            conn.commit()

        for release in data.get('releases', []):
            bi = release.get('basic_information', {})
            discogs_id = bi.get('id')
            release_id = f"release_{discogs_id}"
            catno_parts = []
            for lbl in (bi.get('labels') or []):
                if isinstance(lbl, dict):
                    c = lbl.get('catno', '')
                    if c: catno_parts.append(c)

            row = {
                'release_id': release_id,
                'collection_id': collection_id,
                'basic_information': json.dumps(bi),
                'discogs_id': discogs_id,
                'title': bi.get('title', ''),
                'artist': safe_join(bi.get('artists')),
                'year': bi.get('year') or None,
                'label': safe_join(bi.get('labels')),
                'catno': ', '.join(catno_parts),
                'format': safe_join(bi.get('formats')),
                'genres': json.dumps(safe_list(bi.get('genres'))),
                'styles': json.dumps(safe_list(bi.get('styles'))),
                'producers': json.dumps([]),
                'country': bi.get('country'),
                'date_added': release.get('date_added'),
                'instance_id': release.get('instance_id'),
                'folder_id': release.get('folder_id'),
                'rating': release.get('rating'),
                'copies_count': 1,
                'instance_ids': json.dumps([release.get('instance_id')] if release.get('instance_id') else []),
                'notes': None,
                'condition': None,
                'sleeve_condition': None,
                'marketplace_stats': json.dumps({}),
                'artwork_urls': json.dumps([]),
                'local_artwork_paths': json.dumps([]),
                'raw_data': json.dumps(release),
                'community_have_count': 0,
                'community_want_count': 0,
                'community_rating_count': 0,
                'community_average_rating': 0.0,
                'stats_last_updated': None,
            }

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO releases (
                        release_id, collection_id, basic_information, discogs_id, title, artist, year,
                        label, catno, format, genres, styles, copies_count, instance_ids, producers,
                        country, date_added, instance_id, folder_id, rating, notes, condition,
                        sleeve_condition, marketplace_stats, artwork_urls, local_artwork_paths,
                        community_have_count, community_want_count, community_rating_count,
                        community_average_rating, stats_last_updated, raw_data
                    ) VALUES (
                        %(release_id)s, %(collection_id)s, %(basic_information)s, %(discogs_id)s,
                        %(title)s, %(artist)s, %(year)s, %(label)s, %(catno)s, %(format)s,
                        %(genres)s, %(styles)s, %(copies_count)s, %(instance_ids)s, %(producers)s,
                        %(country)s, %(date_added)s, %(instance_id)s, %(folder_id)s, %(rating)s,
                        %(notes)s, %(condition)s, %(sleeve_condition)s, %(marketplace_stats)s,
                        %(artwork_urls)s, %(local_artwork_paths)s, %(community_have_count)s,
                        %(community_want_count)s, %(community_rating_count)s,
                        %(community_average_rating)s, %(stats_last_updated)s, %(raw_data)s
                    )
                    ON CONFLICT (release_id) DO UPDATE SET
                        basic_information = EXCLUDED.basic_information,
                        title = EXCLUDED.title, artist = EXCLUDED.artist, year = EXCLUDED.year,
                        label = EXCLUDED.label, catno = EXCLUDED.catno, format = EXCLUDED.format,
                        genres = EXCLUDED.genres, styles = EXCLUDED.styles,
                        country = EXCLUDED.country, date_added = EXCLUDED.date_added,
                        instance_id = EXCLUDED.instance_id, folder_id = EXCLUDED.folder_id,
                        raw_data = EXCLUDED.raw_data, last_updated = NOW()
                """, row)

            imported += 1

        conn.commit()
        print(f"  Imported {imported}/{total} releases")

        if data['pagination']['page'] >= data['pagination']['pages']:
            break
        page += 1

    print(f"\nDone! {imported} releases imported.")
    conn.close()

if __name__ == '__main__':
    main()
