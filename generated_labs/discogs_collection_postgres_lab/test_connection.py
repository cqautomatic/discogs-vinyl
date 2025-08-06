#!/usr/bin/env python3
"""
Test script for PostgreSQL connection and basic functionality
"""

import os
import sys
import json
from pathlib import Path
import psycopg2
import psycopg2.extras

def test_connection():
    """Test PostgreSQL connection and basic operations."""
    print("🐘 Testing PostgreSQL Connection for Discogs Collection Lab")
    print("=" * 60)
    
    # Try to load configuration
    try:
        # First try environment variables
        config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DATABASE', 'discogs_collection'),
            'user': os.getenv('POSTGRES_USER', 'discogs_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'discogs_password')
        }
        
        # If no environment variables, try config file
        if not config['password'] or config['password'] == 'discogs_password':
            config_file = Path('discogs_config.json')
            if config_file.exists():
                with open(config_file) as f:
                    file_config = json.load(f)
                    config.update({
                        'host': file_config.get('postgres_host', config['host']),
                        'port': file_config.get('postgres_port', config['port']),
                        'database': file_config.get('postgres_database', config['database']),
                        'user': file_config.get('postgres_user', config['user']),
                        'password': file_config.get('postgres_password', config['password'])
                    })
        
        print(f"Connection parameters:")
        print(f"  Host: {config['host']}")
        print(f"  Port: {config['port']}")
        print(f"  Database: {config['database']}")
        print(f"  User: {config['user']}")
        print(f"  Password: {'*' * len(config['password'])}")
        print()
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    # Test connection
    try:
        print("📡 Connecting to PostgreSQL...")
        connection = psycopg2.connect(**config)
        print("✅ Connection successful!")
        
        # Test basic query
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"📊 PostgreSQL version: {version}")
        
        # Check if our schema exists
        schema_name = os.getenv('POSTGRES_SCHEMA', 'collection_data')
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """, (schema_name,))
            
            if cursor.fetchone():
                print(f"✅ Schema '{schema_name}' exists")
                
                # Set search path and check tables
                cursor.execute(f"SET search_path TO {schema_name}, public")
                
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                """, (schema_name,))
                
                tables = [row[0] for row in cursor.fetchall()]
                if tables:
                    print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
                    
                    # Test if we can query a table
                    if 'collections' in tables:
                        cursor.execute("SELECT COUNT(*) FROM collections")
                        count = cursor.fetchone()[0]
                        print(f"📊 Collections table has {count} records")
                    
                    if 'releases' in tables:
                        cursor.execute("SELECT COUNT(*) FROM releases")
                        count = cursor.fetchone()[0]
                        print(f"🎵 Releases table has {count} records")
                else:
                    print("⚠️  No tables found in schema. You may need to run setup.sql")
            else:
                print(f"⚠️  Schema '{schema_name}' not found. You may need to run setup.sql")
        
        # Test JSONB functionality
        print("\n🧪 Testing JSONB functionality...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT jsonb_build_object('test', 'value', 'array', jsonb_build_array(1, 2, 3))
            """)
            result = cursor.fetchone()[0]
            print(f"✅ JSONB test successful: {result}")
        
        # Test full-text search capabilities
        print("\n🔍 Testing full-text search capabilities...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT to_tsvector('english', 'The quick brown fox jumps over the lazy dog')
            """)
            result = cursor.fetchone()[0]
            print(f"✅ Full-text search test successful")
        
        # Test extensions
        print("\n🔧 Checking PostgreSQL extensions...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname IN ('uuid-ossp', 'pg_trgm')
            """)
            extensions = cursor.fetchall()
            
            for ext_name, ext_version in extensions:
                print(f"✅ Extension {ext_name} v{ext_version} is installed")
            
            if len(extensions) < 2:
                print("⚠️  Some extensions may be missing. Check setup.sql")
        
        connection.close()
        print("\n🎉 All tests passed! PostgreSQL is ready for Discogs collection data.")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure PostgreSQL is running")
        print("   2. Check your connection parameters")
        print("   3. Verify the database exists")
        print("   4. Check pg_hba.conf for authentication settings")
        print("   5. Try running: docker-compose up -d postgres")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_discogs_api():
    """Test if Discogs API token is configured."""
    print("\n🎵 Testing Discogs API Configuration")
    print("=" * 40)
    
    token = os.getenv('DISCOGS_TOKEN')
    if not token:
        # Try config file
        config_file = Path('discogs_config.json')
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                token = config.get('token')
    
    if token and token != 'YOUR_DISCOGS_TOKEN_HERE':
        print(f"✅ Discogs token configured (length: {len(token)})")
        
        # Test a simple API call
        try:
            import requests
            headers = {
                'Authorization': f'Discogs token={token}',
                'User-Agent': 'DiscogsCollectionTest/1.0'
            }
            
            response = requests.get('https://api.discogs.com/oauth/identity', headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API test successful! User: {data.get('username', 'Unknown')}")
                return True
            else:
                print(f"❌ API test failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ API test error: {e}")
            return False
    else:
        print("⚠️  Discogs API token not configured")
        print("   Set DISCOGS_TOKEN environment variable or update discogs_config.json")
        return False

def main():
    """Run all tests."""
    db_success = test_connection()
    api_success = test_discogs_api()
    
    print("\n" + "=" * 60)
    if db_success and api_success:
        print("🎉 All systems ready! You can now run:")
        print("   python discogs_downloader.py --max-releases 5")
        print("   streamlit run streamlit_app.py")
    elif db_success:
        print("✅ Database ready, but configure your Discogs API token first")
    else:
        print("❌ Setup incomplete. Please check the errors above.")

if __name__ == "__main__":
    main()