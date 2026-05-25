#!/usr/bin/env python3
"""
Test script for artist refresh functionality
"""

import sys
import os
from pathlib import Path

# Add the project directory to Python path
app_dir = Path(__file__).resolve().parents[1] / 'apps' / 'postgres' / 'discogs_collection_postgres_lab'
sys.path.insert(0, str(app_dir))

from discogs_downloader import DiscogsAPI, load_config
from core.database import PostgreSQLConnection
import json

def test_artist_refresh():
    """Test refreshing artist data directly"""
    
    # Load configuration (includes token from secrets.toml)
    try:
        config = load_config()
        token = config.token
    except Exception as e:
        print(f"ERROR: Could not load config: {e}")
        return False
    
    if not token:
        print("ERROR: No Discogs token found in configuration")
        return False
    
    api = DiscogsAPI(token, "ArtistRefreshTest/1.0")
    db = PostgreSQLConnection()
    
    if not db.connection:
        print("ERROR: Could not connect to database")
        return False
    
    # Test with Dave Lee (ID 22312)
    artist_id = 22312
    print(f"Fetching artist data for ID {artist_id}...")
    
    artist_data = api.get_artist_details(artist_id)
    if not artist_data:
        print("ERROR: Could not fetch artist data from Discogs API")
        return False
    
    print(f"Fetched data for: {artist_data.get('name')}")
    print(f"Aliases: {len(artist_data.get('aliases', []))} found")
    print(f"Groups: {len(artist_data.get('groups', []))} found")
    
    # Update database
    query = """
    UPDATE artists 
    SET 
        real_name = %s,
        profile = %s,
        images = %s,
        urls = %s,
        members = %s,
        groups = %s,
        aliases = %s,
        raw_data = %s,
        last_updated = CURRENT_TIMESTAMP
    WHERE discogs_artist_id = %s
    """
    
    try:
        with db.connection.cursor() as cursor:
            cursor.execute(query, (
                artist_data.get('real_name'),
                artist_data.get('profile'),
                json.dumps(artist_data.get('images', [])),
                json.dumps(artist_data.get('urls', [])),
                json.dumps(artist_data.get('members', [])),
                json.dumps(artist_data.get('groups', [])),
                json.dumps(artist_data.get('aliases', [])),
                json.dumps(artist_data),
                artist_id
            ))
        db.connection.commit()
        
        print("✅ Successfully updated artist data in database")
        
        # Verify the update
        result = db.execute_query("""
            SELECT artist_name, real_name, aliases, groups 
            FROM artists 
            WHERE discogs_artist_id = %s
        """, (artist_id,))
        
        if result:
            artist = result[0]
            print(f"✅ Verified: {artist['artist_name']}")
            
            # Handle both string and already-parsed JSON
            aliases_raw = artist['aliases']
            if isinstance(aliases_raw, str):
                aliases = json.loads(aliases_raw or '[]')
            else:
                aliases = aliases_raw or []
                
            groups_raw = artist['groups'] 
            if isinstance(groups_raw, str):
                groups = json.loads(groups_raw or '[]')
            else:
                groups = groups_raw or []
                
            print(f"✅ Aliases: {len(aliases)} (first few: {[a['name'] for a in aliases[:3]]})")
            print(f"✅ Groups: {len(groups)} (first few: {[g['name'] for g in groups[:3]]})")
            
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to update database: {e}")
        return False

if __name__ == "__main__":
    success = test_artist_refresh()
    sys.exit(0 if success else 1)