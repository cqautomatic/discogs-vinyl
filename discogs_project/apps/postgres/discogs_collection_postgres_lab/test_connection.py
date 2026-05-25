#!/usr/bin/env python3
"""Test script for PostgreSQL connection"""

from core.database import PostgreSQLConnection
from core.config import load_config

def test_connection():
    """Test the database connection with current configuration."""
    print("🔗 Testing PostgreSQL connection...")
    
    try:
        # Load configuration
        config = load_config()
        print(f"📡 Connecting to: {config.postgres_host}:{config.postgres_port}")
        print(f"🗄️  Database: {config.postgres_database}")
        print(f"👤 User: {config.postgres_user}")
        
        # Test connection
        db_conn = PostgreSQLConnection()
        
        if db_conn.connection:
            print("✅ Database connection successful!")
            
            # Test basic query
            result = db_conn.execute_query("SELECT COUNT(*) as release_count FROM releases")
            if result:
                print(f"📀 Found {result[0]['release_count']} releases in collection")
            
            # Test artwork table
            artwork_result = db_conn.execute_query("SELECT COUNT(*) as artwork_count FROM artwork")
            if artwork_result:
                print(f"🖼️  Found {artwork_result[0]['artwork_count']} artwork files")
            
            return True
        else:
            print("❌ Database connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    test_connection()

