#!/usr/bin/env python3
"""
Refresh pricing data specifically for wantlist items.
"""

import sys
import os
import time
import requests
import psycopg2
import psycopg2.extras
import toml

sys.path.append('.')

def connect_database():
    """Connect to PostgreSQL using secrets.toml."""
    secrets = toml.load('.streamlit/secrets.toml')
    pg_config = secrets['postgres']
    
    return psycopg2.connect(
        host=pg_config['host'],
        port=pg_config['port'],
        user=pg_config['user'],
        password=pg_config['password'],
        database=pg_config['database'],
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def get_discogs_token():
    """Get Discogs token from secrets."""
    secrets = toml.load('.streamlit/secrets.toml')
    return secrets['discogs']['token']

def fetch_marketplace_stats(release_id: int, token: str):
    """Fetch marketplace statistics from Discogs API."""
    url = f"https://api.discogs.com/marketplace/stats/{release_id}"
    headers = {
        'User-Agent': 'DiscogsWantlistPricing/1.0',
        'Authorization': f'Discogs token={token}'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"  No marketplace data for release {release_id}")
            return None
        elif response.status_code == 429:
            print(f"  Rate limited, waiting 60 seconds...")
            time.sleep(60)
            return fetch_marketplace_stats(release_id, token)  # Retry
        else:
            print(f"  API error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"  Request failed for release {release_id}: {e}")
        return None

def refresh_wantlist_prices(batch_limit: int = 50):
    """Refresh pricing data for wantlist items."""
    token = get_discogs_token()
    conn = connect_database()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SET search_path TO collection_data, public")
        
        print(f"🔍 Finding wantlist items needing price updates...")
        
        # Get wantlist items that don't have pricing data or have stale data
        query = """
        SELECT DISTINCT w.discogs_release_id as rid, w.title, w.artist
        FROM wantlist w
        LEFT JOIN release_prices p ON p.discogs_release_id = w.discogs_release_id
        WHERE w.discogs_release_id IS NOT NULL
          AND (p.discogs_release_id IS NULL OR p.last_seen < NOW() - INTERVAL '24 hours')
        ORDER BY w.discogs_release_id
        LIMIT %s
        """
        
        cursor.execute(query, (batch_limit,))
        candidates = cursor.fetchall()
        
        print(f"📋 Found {len(candidates)} wantlist items to update pricing for")
        
        if not candidates:
            print("✅ All wantlist items have current pricing data!")
            return
        
        successful_updates = 0
        
        for i, item in enumerate(candidates, 1):
            release_id = item['rid']
            title = item['title'][:50] + '...' if len(item['title']) > 50 else item['title']
            
            print(f"  {i}/{len(candidates)}: {title}")
            
            # Fetch pricing data from Discogs API
            pricing_data = fetch_marketplace_stats(release_id, token)
            
            if pricing_data:
                lowest = pricing_data.get('lowest_price')
                num_for_sale = pricing_data.get('num_for_sale', 0)
                
                # Insert or update pricing data
                upsert_query = """
                INSERT INTO release_prices (
                    discogs_release_id, 
                    lowest_price, 
                    currency, 
                    num_for_sale, 
                    availability, 
                    last_seen,
                    source
                )
                VALUES (%s, %s, %s, %s, %s, NOW(), 'wantlist_refresh')
                ON CONFLICT (discogs_release_id) 
                DO UPDATE SET 
                    lowest_price = EXCLUDED.lowest_price,
                    currency = EXCLUDED.currency,
                    num_for_sale = EXCLUDED.num_for_sale,
                    availability = EXCLUDED.availability,
                    last_seen = NOW(),
                    source = EXCLUDED.source
                """
                
                price_val = float(lowest['value']) if lowest else None
                currency_val = lowest['currency'] if lowest else 'USD'
                availability = num_for_sale > 0
                
                cursor.execute(upsert_query, (
                    release_id,
                    price_val,
                    currency_val, 
                    num_for_sale,
                    availability
                ))
                
                conn.commit()
                successful_updates += 1
                
                print(f"    ✅ Updated: {currency_val} {price_val} ({num_for_sale} for sale)")
            else:
                # Insert a record showing we checked but found no data
                cursor.execute("""
                INSERT INTO release_prices (
                    discogs_release_id, 
                    lowest_price, 
                    currency, 
                    num_for_sale, 
                    availability, 
                    last_seen,
                    source
                )
                VALUES (%s, NULL, NULL, 0, FALSE, NOW(), 'wantlist_refresh_no_data')
                ON CONFLICT (discogs_release_id) 
                DO UPDATE SET 
                    last_seen = NOW(),
                    source = EXCLUDED.source
                """, (release_id,))
                conn.commit()
            
            # Rate limiting - be nice to Discogs API
            time.sleep(1)
        
        print(f"\n🎉 Pricing refresh complete!")
        print(f"   Successfully updated: {successful_updates}/{len(candidates)} items")
        
    except Exception as e:
        print(f"❌ Error during pricing refresh: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Refresh pricing for wantlist items')
    parser.add_argument('--batch-limit', type=int, default=50, 
                       help='Maximum number of items to process (default: 50)')
    args = parser.parse_args()
    
    refresh_wantlist_prices(args.batch_limit)