#!/usr/bin/env python3
"""
Test the exact SQL query used by load_wantlist_items function.
"""

import sys
import os
import psycopg2
import psycopg2.extras
import pandas as pd

sys.path.append('.')

def connect_direct_postgres():
    """Connect directly using secrets.toml config."""
    import toml
    
    secrets_path = '.streamlit/secrets.toml'
    if os.path.exists(secrets_path):
        secrets = toml.load(secrets_path)
        pg_config = secrets['postgres']
        
        return psycopg2.connect(
            host=pg_config['host'],
            port=pg_config['port'],
            user=pg_config['user'],
            password=pg_config['password'],
            database=pg_config['database'],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    else:
        raise Exception("secrets.toml not found")

def test_streamlit_query():
    """Test the exact query used by load_wantlist_items."""
    conn = None
    try:
        print("=== TESTING STREAMLIT QUERY ===")
        conn = connect_direct_postgres()
        
        # Set search path like Streamlit does
        cursor = conn.cursor()
        cursor.execute("SET search_path TO collection_data, public")
        
        # This is the exact query from load_wantlist_items function
        query = """
        SELECT 
            w.discogs_release_id,
            w.title,
            w.artist,
            w.year,
            w.label,
            w.format,
            w.genres,
            w.styles,
            w.notes,
            w.rating,
            w.added,
            rp.lowest_price,
            rp.currency,
            rp.num_for_sale,
            rp.availability,
            rp.last_seen as price_last_seen
        FROM wantlist w
        LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
        ORDER BY 
            CASE WHEN rp.availability = true THEN 0 ELSE 1 END,
            rp.lowest_price ASC NULLS LAST,
            w.added DESC
        LIMIT 10
        """
        
        print("Executing query...")
        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"✅ Query returned {len(results)} rows")
        
        if results:
            print("\nSample results:")
            for i, row in enumerate(results[:5]):
                price = row['lowest_price'] if row['lowest_price'] else 'NULL'
                currency = row['currency'] if row['currency'] else 'NULL' 
                available = row['availability'] if row['availability'] is not None else 'NULL'
                
                print(f"\n{i+1}. {row['title'][:50]}...")
                print(f"   Artist: {row['artist']}")
                print(f"   Price: {price} {currency}")
                print(f"   Available: {available}")
                print(f"   Release ID: {row['discogs_release_id']}")
        
        # Test the core.database connection method
        print(f"\n=== TESTING CORE.DATABASE CONNECTION ===")
        from core.database import PostgreSQLConnection
        
        db = PostgreSQLConnection()
        streamlit_result = db.execute_query(query)
        
        if streamlit_result:
            print(f"✅ Core database connection returned {len(streamlit_result)} rows")
            
            # Check if it's the same data
            if len(streamlit_result) == len(results):
                print("✅ Results match between direct connection and core.database")
            else:
                print(f"⚠️  Result count mismatch: direct={len(results)}, core={len(streamlit_result)}")
        else:
            print("❌ Core database connection returned no results")
            
    except Exception as e:
        print(f"❌ Error during query test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_streamlit_query()