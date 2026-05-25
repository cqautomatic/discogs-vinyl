#!/usr/bin/env python3
"""Test script for duplicate detection query"""

from core.database import PostgreSQLConnection
import pandas as pd

def test_duplicate_query():
    """Test the duplicate detection query to ensure it works."""
    print("🔗 Testing duplicate detection query...")
    
    try:
        db_conn = PostgreSQLConnection()
        
        if not db_conn.connection:
            print("❌ Database connection failed!")
            return False
        
        # Test the exact query from Master Release Tracking
        duplicate_query = """
        SELECT 
            title, 
            artist, 
            COUNT(*) as version_count,
            STRING_AGG(DISTINCT format, ', ') as formats,
            STRING_AGG(DISTINCT country, ', ') as countries,
            MIN(year) as earliest_year,
            MAX(year) as latest_year
        FROM releases
        WHERE title IS NOT NULL AND artist IS NOT NULL
        GROUP BY title, artist
        HAVING COUNT(*) > 1
        ORDER BY version_count DESC
        LIMIT 5
        """
        
        print("📊 Executing duplicate detection query...")
        result = db_conn.execute_query(duplicate_query)
        
        if result:
            df = pd.DataFrame(result)
            print(f"✅ Query successful! Found {len(df)} duplicate groups:")
            
            for idx, row in df.iterrows():
                print(f"  🎵 {row['artist']} - {row['title']} ({row['version_count']} versions)")
                print(f"     Formats: {row['formats']}")
                print(f"     Countries: {row['countries']}")
                print(f"     Years: {row['earliest_year']}-{row['latest_year']}")
                print()
            
            return True
        else:
            print("⚠️  Query returned no results (no duplicates found)")
            return True
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        print("\n🔍 Debugging info:")
        print("This error suggests the database schema might be different than expected.")
        print("Let's check the releases table structure...")
        
        try:
            # Check table structure
            schema_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'releases'
            ORDER BY ordinal_position
            """
            schema_result = db_conn.execute_query(schema_query)
            if schema_result:
                print("\n📋 Releases table columns:")
                for col in schema_result:
                    print(f"  - {col['column_name']}: {col['data_type']}")
        except Exception as schema_e:
            print(f"❌ Could not check schema: {schema_e}")
        
        return False

if __name__ == "__main__":
    test_duplicate_query()

