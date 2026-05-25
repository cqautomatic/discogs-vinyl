#!/usr/bin/env python3
"""
Standalone script to refresh artist detailed information.
Works around connection issues in the main downloader.
"""

import sys
import time
import json
from pathlib import Path

# Add the project directory to Python path
app_dir = Path(__file__).resolve().parents[1] / 'apps' / 'postgres' / 'discogs_collection_postgres_lab'
sys.path.insert(0, str(app_dir))

from discogs_downloader import DiscogsAPI, load_config
from core.database import PostgreSQLConnection

def refresh_artist_data(api, db, artist_id, artist_name):
    """Refresh a single artist's data."""
    try:
        # Fetch from Discogs API
        artist_data = api.get_artist_details(artist_id)
        if not artist_data:
            print(f"❌ Could not fetch data for {artist_name} (ID: {artist_id})")
            return False
        
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
        
        aliases_count = len(artist_data.get('aliases', []))
        groups_count = len(artist_data.get('groups', []))
        print(f"✅ {artist_name} - {aliases_count} aliases, {groups_count} groups")
        return True
        
    except Exception as e:
        print(f"❌ Error refreshing {artist_name}: {e}")
        return False

def main():
    """Main refresh function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Refresh artist detailed information')
    parser.add_argument('--batch-size', type=int, help='Number of artists to process')
    parser.add_argument('--artist-id', type=int, help='Refresh specific artist by ID')
    parser.add_argument('--artist-name', type=str, help='Refresh specific artist by name')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config()
        api = DiscogsAPI(config.token, "ArtistRefresh/1.0")
        db = PostgreSQLConnection()
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    if not db.connection:
        print("❌ Database connection failed")
        return False
    
    # Handle specific artist requests
    if args.artist_id:
        print(f"Refreshing artist ID {args.artist_id}...")
        return refresh_artist_data(api, db, args.artist_id, f"Artist-{args.artist_id}")
    
    if args.artist_name:
        # Find artist by name
        query = """
        SELECT discogs_artist_id, artist_name 
        FROM artists 
        WHERE LOWER(artist_name) LIKE LOWER(%s)
        LIMIT 1
        """
        result = db.execute_query(query, (f'%{args.artist_name}%',))
        if result:
            artist_id = result[0]['discogs_artist_id']
            artist_name = result[0]['artist_name']
            print(f"Found {artist_name} (ID: {artist_id})")
            return refresh_artist_data(api, db, artist_id, artist_name)
        else:
            print(f"❌ Artist '{args.artist_name}' not found")
            return False
    
    # Batch processing
    if args.batch_size:
        query = """
        SELECT discogs_artist_id, artist_name 
        FROM artists 
        WHERE discogs_artist_id IS NOT NULL 
        AND (real_name IS NULL OR aliases IS NULL OR groups IS NULL)
        ORDER BY last_updated ASC
        LIMIT %s
        """
        artists = db.execute_query(query, (args.batch_size,))
    else:
        query = """
        SELECT discogs_artist_id, artist_name 
        FROM artists 
        WHERE discogs_artist_id IS NOT NULL 
        AND (real_name IS NULL OR aliases IS NULL OR groups IS NULL)
        ORDER BY last_updated ASC
        """
        artists = db.execute_query(query)
    
    if not artists:
        print("✅ No artists need refreshing")
        return True
    
    print(f"🚀 Refreshing {len(artists)} artists...")
    success_count = 0
    
    for i, artist in enumerate(artists, 1):
        artist_id = artist['discogs_artist_id']
        artist_name = artist['artist_name']
        
        print(f"[{i}/{len(artists)}] {artist_name} (ID: {artist_id})", end=" - ")
        
        if refresh_artist_data(api, db, artist_id, artist_name):
            success_count += 1
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n🎉 Completed: {success_count}/{len(artists)} artists updated successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)