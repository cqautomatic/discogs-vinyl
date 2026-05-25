#!/usr/bin/env python3
"""
Comprehensive database diagnostic script to find wantlist data location.
"""

import sys
import os
import psycopg2
import psycopg2.extras

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

def diagnose_database():
    """Run comprehensive database diagnostics."""
    conn = None
    try:
        print("=== CONNECTING TO DATABASE ===")
        conn = connect_direct_postgres()
        print("✅ Connected successfully")
        
        cursor = conn.cursor()
        
        print("\n=== CHECKING ALL SCHEMAS ===")
        cursor.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;")
        schemas = cursor.fetchall()
        print("Available schemas:")
        for schema in schemas:
            print(f"  - {schema['schema_name']}")
        
        print("\n=== SEARCHING FOR WANTLIST TABLES ===")
        cursor.execute("""
            SELECT schemaname, tablename, hasindexes, hasrules, hastriggers 
            FROM pg_tables 
            WHERE tablename = 'wantlist'
            ORDER BY schemaname;
        """)
        wantlist_tables = cursor.fetchall()
        
        if wantlist_tables:
            print("Found wantlist tables:")
            for table in wantlist_tables:
                schema = table['schemaname']
                print(f"\n📋 Schema: {schema}")
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) as count FROM {schema}.wantlist;")
                count_result = cursor.fetchone()
                row_count = count_result['count']
                print(f"   Rows: {row_count}")
                
                if row_count > 0:
                    # Get sample data
                    cursor.execute(f"""
                        SELECT discogs_release_id, title, artist, added
                        FROM {schema}.wantlist 
                        LIMIT 3;
                    """)
                    samples = cursor.fetchall()
                    print("   Sample data:")
                    for sample in samples:
                        title = sample['title'][:40] + '...' if len(sample['title']) > 40 else sample['title']
                        print(f"     ID: {sample['discogs_release_id']}, Title: {title}")
                        print(f"         Artist: {sample['artist']}, Added: {sample['added']}")
                
                # Check table structure
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}' AND table_name = 'wantlist'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                print(f"   Columns ({len(columns)}):")
                for col in columns:
                    print(f"     {col['column_name']} ({col['data_type']}) - {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
        else:
            print("❌ No wantlist tables found!")
        
        print("\n=== CHECKING CURRENT SEARCH PATH ===")
        cursor.execute("SHOW search_path;")
        search_path = cursor.fetchone()
        print(f"Current search path: {search_path['search_path']}")
        
        # Test query without schema prefix (like Streamlit does)
        print(f"\n=== TESTING QUERY WITHOUT SCHEMA PREFIX ===")
        try:
            cursor.execute("SELECT COUNT(*) as count FROM wantlist;")
            result = cursor.fetchone()
            print(f"✅ Query successful - found {result['count']} rows")
            
            if result['count'] > 0:
                cursor.execute("SELECT discogs_release_id, title FROM wantlist LIMIT 2;")
                samples = cursor.fetchall()
                print("Sample results:")
                for sample in samples:
                    print(f"  ID: {sample['discogs_release_id']}, Title: {sample['title'][:50]}...")
        except Exception as e:
            print(f"❌ Query failed: {e}")
            
        print("\n=== CHECKING RELEASE_PRICES TABLE ===")
        cursor.execute("""
            SELECT schemaname, tablename
            FROM pg_tables 
            WHERE tablename = 'release_prices'
            ORDER BY schemaname;
        """)
        price_tables = cursor.fetchall()
        
        for table in price_tables:
            schema = table['schemaname']
            print(f"\n💰 release_prices in {schema}:")
            
            cursor.execute(f"SELECT COUNT(*) as total FROM {schema}.release_prices;")
            total = cursor.fetchone()['total']
            
            cursor.execute(f"SELECT COUNT(*) as with_prices FROM {schema}.release_prices WHERE lowest_price IS NOT NULL;")
            with_prices = cursor.fetchone()['with_prices']
            
            print(f"   Total rows: {total}")
            print(f"   Rows with prices: {with_prices}")
            
        print("\n=== DIAGNOSIS COMPLETE ===")
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    diagnose_database()