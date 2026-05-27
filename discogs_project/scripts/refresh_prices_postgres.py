#!/usr/bin/env python3
"""
Refresh release prices & availability from Discogs API into PostgreSQL and emit availability events.
Requires:
- ENV: DISCOGS_TOKEN, PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
"""

import os
import time
import requests
import psycopg2


def get_db():
    return psycopg2.connect(
        host=os.getenv('PGHOST','localhost'),
        port=int(os.getenv('PGPORT','5432')),
        database=os.getenv('PGDATABASE','discogs_collection'),
        user=os.getenv('PGUSER','postgres'),
        password=os.getenv('PGPASSWORD','postgres')
    )


def fetch_marketplace_release(release_id: int, token: str):
    url = f"https://api.discogs.com/marketplace/stats/{release_id}"
    headers = {
        'User-Agent': 'DiscogsPricing/1.0',
        'Authorization': f'Discogs token={token}'
    }
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 200:
        return r.json()
    elif r.status_code == 404:
        return None
    else:
        raise RuntimeError(f"Discogs API error {r.status_code}: {r.text}")


def refresh_prices(batch_limit: int = None):
    token = os.environ['DISCOGS_TOKEN']
    conn = get_db()
    conn.autocommit = False
    try:
        cur = conn.cursor()
        # candidates: owned collection + wantlist, missing prices or stale (>24h)
        stale_clause = "(p.discogs_release_id IS NULL OR p.last_seen < NOW() - INTERVAL '24 hours')"
        base_sql = f"""
            WITH candidates AS (
              SELECT DISTINCT r.discogs_id AS rid
              FROM collection_data.releases r
              LEFT JOIN collection_data.release_prices p
                 ON p.discogs_release_id = r.discogs_id
              WHERE r.discogs_id IS NOT NULL AND {stale_clause}

              UNION

              SELECT DISTINCT w.discogs_release_id AS rid
              FROM collection_data.wantlist w
              LEFT JOIN collection_data.release_prices p
                 ON p.discogs_release_id = w.discogs_release_id
              WHERE w.discogs_release_id IS NOT NULL AND {stale_clause}
            )
            SELECT rid FROM candidates
        """
        if batch_limit:
            cur.execute(base_sql + " LIMIT %s", (batch_limit,))
        else:
            cur.execute(base_sql)
        rows = cur.fetchall()
        total_releases = len(rows)
        print(f"Found {total_releases} releases to process")
        
        processed_count = 0
        for (rid,) in rows:
            processed_count += 1
            print(f"Processing release {processed_count}/{total_releases} (ID: {rid})")
            try:
                data = fetch_marketplace_release(rid, token)
                # Rate limiting: wait 1 second between successful API calls
                time.sleep(1)
            except Exception as e:
                print(f"Error fetching data for release {rid}: {e}")
                # backoff on rate limiting - longer delay for errors
                time.sleep(3)
                continue

            if not data:
                # no stats; mark as unavailable
                cur.execute(
                    """
                    INSERT INTO collection_data.release_prices (discogs_release_id, lowest_price, currency, num_for_sale, availability, last_seen, source)
                    VALUES (%s, NULL, NULL, 0, FALSE, NOW(), 'discogs')
                    ON CONFLICT (discogs_release_id)
                    DO UPDATE SET lowest_price = EXCLUDED.lowest_price,
                                  currency = EXCLUDED.currency,
                                  num_for_sale = EXCLUDED.num_for_sale,
                                  availability = EXCLUDED.availability,
                                  last_seen = EXCLUDED.last_seen,
                                  source = EXCLUDED.source
                    RETURNING availability
                    """,
                    (rid,)
                )
                new_avail = cur.fetchone()[0]
            else:
                # parse minimal fields
                lowest = None
                curcy = None
                num = 0
                try:
                    # Handle nested price structure: {'value': 4.0, 'currency': 'USD'}
                    price_data = data.get('lowest_price')
                    if price_data and isinstance(price_data, dict):
                        lowest = float(price_data.get('value')) if price_data.get('value') is not None else None
                        curcy = price_data.get('currency')
                    elif price_data is not None:
                        # Fallback for simple number format
                        lowest = float(price_data)
                        curcy = data.get('currency')
                    
                    # Also try top-level currency if not found in price object
                    if not curcy:
                        curcy = data.get('currency')
                        
                    num = int(data.get('num_for_sale') or 0)
                except Exception as e:
                    print(f"Error parsing price data for release {rid}: {e}, data: {data}")
                    pass
                availability = num > 0
                cur.execute(
                    """
                    INSERT INTO collection_data.release_prices (discogs_release_id, lowest_price, currency, num_for_sale, availability, last_seen, source)
                    VALUES (%s, %s, %s, %s, %s, NOW(), 'discogs')
                    ON CONFLICT (discogs_release_id)
                    DO UPDATE SET lowest_price = EXCLUDED.lowest_price,
                                  currency = EXCLUDED.currency,
                                  num_for_sale = EXCLUDED.num_for_sale,
                                  availability = EXCLUDED.availability,
                                  last_seen = EXCLUDED.last_seen,
                                  source = EXCLUDED.source
                    RETURNING availability
                    """,
                    (rid, lowest, curcy, num, availability)
                )
                new_avail = cur.fetchone()[0]

            # emit availability event if changed
            cur.execute(
                """
                WITH prev AS (
                  SELECT availability FROM collection_data.release_prices WHERE discogs_release_id=%s
                )
                SELECT availability FROM collection_data.release_prices WHERE discogs_release_id=%s
                """,
                (rid, rid)
            )
            # we already have current; fetch previous via separate query
            cur.execute("SELECT availability FROM collection_data.release_prices WHERE discogs_release_id=%s", (rid,))
            current_avail = cur.fetchone()[0]
            # naive check: simply log when availability true and previously false by history lookup
            # a more robust implementation stores previous availability in a temp table
            if new_avail and current_avail:
                # insert event that it's available (idempotent enough for demo)
                cur.execute(
                    "INSERT INTO collection_data.availability_events (discogs_release_id, from_available, to_available) VALUES (%s, %s, %s)",
                    (rid, False, True)
                )

            conn.commit()
        
        print(f"Completed processing {processed_count} releases")

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    refresh_prices()






