#!/usr/bin/env python3
"""
Discogs Collection Downloader
Downloads collection data and artwork from Discogs API and stores in Snowflake.
"""

import os
import sys
import time
import json
import uuid
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import snowflake.connector
from snowflake.connector import DictCursor
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discogs_downloader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DiscogsConfig:
    """Configuration for Discogs API and Snowflake connection."""
    token: str
    user_agent: str
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str
    snowflake_database: str = "DISCOGS_COLLECTION"
    snowflake_schema: str = "COLLECTION_DATA"
    artwork_stage: str = "ARTWORK_STAGE"
    local_artwork_path: str = "./artwork"
    rate_limit_delay: float = 1.0  # Seconds between API calls

class DiscogsAPI:
    """Wrapper for Discogs API interactions."""
    
    def __init__(self, token: str, user_agent: str, rate_limit_delay: float = 1.0):
        self.token = token
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.base_url = "https://api.discogs.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Discogs token={token}',
            'User-Agent': user_agent
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting to respect Discogs API limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a rate-limited request to the Discogs API."""
        self._rate_limit()
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(endpoint, params)
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return None
    
    def get_user_identity(self) -> Optional[Dict]:
        """Get the authenticated user's identity."""
        return self._make_request("/oauth/identity")
    
    def get_user_collection(self, username: str, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get user's collection with pagination."""
        return self._make_request(f"/users/{username}/collection/folders/0/releases", {
            'page': page,
            'per_page': per_page
        })
    
    def get_release_details(self, release_id: int) -> Optional[Dict]:
        """Get detailed information about a specific release."""
        return self._make_request(f"/releases/{release_id}")
    
    def get_master_release(self, master_id: int) -> Optional[Dict]:
        """Get master release information."""
        return self._make_request(f"/masters/{master_id}")
    
    def get_artist_details(self, artist_id: int) -> Optional[Dict]:
        """Get detailed artist information."""
        return self._make_request(f"/artists/{artist_id}")
    
    def get_label_details(self, label_id: int) -> Optional[Dict]:
        """Get detailed label information."""
        return self._make_request(f"/labels/{label_id}")

class ArtworkDownloader:
    """Handles downloading and managing artwork files."""
    
    def __init__(self, local_path: str = "./artwork"):
        self.local_path = Path(local_path)
        self.local_path.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, image_url: str, release_id: str, image_type: str = "primary") -> Optional[Tuple[str, Dict]]:
        """Download an image and return local path and metadata."""
        try:
            response = requests.get(image_url, stream=True)
            if response.status_code != 200:
                logger.warning(f"Failed to download image: {image_url}")
                return None
            
            # Generate filename based on URL hash and release ID
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
            file_extension = image_url.split('.')[-1].lower()
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                file_extension = 'jpg'
            
            filename = f"{release_id}_{image_type}_{url_hash}.{file_extension}"
            local_file_path = self.local_path / filename
            
            # Download and save the file
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get image metadata
            file_size = local_file_path.stat().st_size
            
            # Try to get image dimensions (requires PIL)
            width, height = None, None
            try:
                from PIL import Image
                with Image.open(local_file_path) as img:
                    width, height = img.size
            except ImportError:
                logger.debug("PIL not available, skipping image dimension detection")
            except Exception as e:
                logger.debug(f"Could not get image dimensions: {e}")
            
            metadata = {
                'local_file_path': str(local_file_path),
                'file_size': file_size,
                'image_width': width,
                'image_height': height,
                'file_format': file_extension,
                'download_date': datetime.now()
            }
            
            logger.info(f"Downloaded artwork: {filename} ({file_size} bytes)")
            return str(local_file_path), metadata
            
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            return None

class SnowflakeManager:
    """Manages Snowflake database operations."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.connection = None
    
    def connect(self):
        """Establish connection to Snowflake."""
        try:
            self.connection = snowflake.connector.connect(
                account=self.config.snowflake_account,
                user=self.config.snowflake_user,
                password=self.config.snowflake_password,
                warehouse=self.config.snowflake_warehouse,
                database=self.config.snowflake_database,
                schema=self.config.snowflake_schema
            )
            logger.info("Connected to Snowflake successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise
    
    def disconnect(self):
        """Close Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """Execute a query and return results."""
        try:
            cursor = self.connection.cursor(DictCursor)
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    def upsert_collection(self, collection_data: Dict):
        """Insert or update collection information."""
        query = """
        MERGE INTO COLLECTIONS c
        USING (SELECT %s as COLLECTION_ID, %s as USER_ID, %s as USERNAME, 
                      %s as COLLECTION_NAME, %s as TOTAL_ITEMS) src
        ON c.COLLECTION_ID = src.COLLECTION_ID
        WHEN MATCHED THEN 
            UPDATE SET USER_ID = src.USER_ID, USERNAME = src.USERNAME,
                      COLLECTION_NAME = src.COLLECTION_NAME, TOTAL_ITEMS = src.TOTAL_ITEMS,
                      LAST_UPDATED = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
            INSERT (COLLECTION_ID, USER_ID, USERNAME, COLLECTION_NAME, TOTAL_ITEMS)
            VALUES (src.COLLECTION_ID, src.USER_ID, src.USERNAME, src.COLLECTION_NAME, src.TOTAL_ITEMS)
        """
        
        params = (
            collection_data['collection_id'],
            collection_data['user_id'],
            collection_data['username'],
            collection_data['collection_name'],
            collection_data['total_items']
        )
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
    
    def upsert_release(self, release_data: Dict):
        """Insert or update release information."""
        query = """
        MERGE INTO RELEASES r
        USING (SELECT %s as RELEASE_ID) src
        ON r.RELEASE_ID = src.RELEASE_ID
        WHEN MATCHED THEN 
            UPDATE SET BASIC_INFORMATION = PARSE_JSON(%s),
                      DISCOGS_ID = %s, TITLE = %s, ARTIST = %s, YEAR = %s,
                      LABEL = %s, CATNO = %s, FORMAT = %s, GENRES = PARSE_JSON(%s),
                      STYLES = PARSE_JSON(%s), COUNTRY = %s, DATE_ADDED = %s,
                      INSTANCE_ID = %s, FOLDER_ID = %s, RATING = %s, NOTES = %s,
                      CONDITION = %s, SLEEVE_CONDITION = %s,
                      MARKETPLACE_STATS = PARSE_JSON(%s), ARTWORK_URLS = PARSE_JSON(%s),
                      LOCAL_ARTWORK_PATHS = PARSE_JSON(%s), RAW_DATA = PARSE_JSON(%s),
                      LAST_UPDATED = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
            INSERT (RELEASE_ID, COLLECTION_ID, BASIC_INFORMATION, DISCOGS_ID, TITLE, ARTIST, YEAR,
                   LABEL, CATNO, FORMAT, GENRES, STYLES, COUNTRY, DATE_ADDED, INSTANCE_ID,
                   FOLDER_ID, RATING, NOTES, CONDITION, SLEEVE_CONDITION, MARKETPLACE_STATS,
                   ARTWORK_URLS, LOCAL_ARTWORK_PATHS, RAW_DATA)
            VALUES (%s, %s, PARSE_JSON(%s), %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s),
                   PARSE_JSON(%s), %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s),
                   PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s))
        """
        
        # Prepare JSON fields
        basic_info_json = json.dumps(release_data.get('basic_information', {}))
        genres_json = json.dumps(release_data.get('genres', []))
        styles_json = json.dumps(release_data.get('styles', []))
        marketplace_stats_json = json.dumps(release_data.get('marketplace_stats', {}))
        artwork_urls_json = json.dumps(release_data.get('artwork_urls', []))
        local_artwork_paths_json = json.dumps(release_data.get('local_artwork_paths', []))
        raw_data_json = json.dumps(release_data.get('raw_data', {}))
        
        params = (
            # For UPDATE
            basic_info_json, release_data.get('discogs_id'), release_data.get('title'),
            release_data.get('artist'), release_data.get('year'), release_data.get('label'),
            release_data.get('catno'), release_data.get('format'), genres_json, styles_json,
            release_data.get('country'), release_data.get('date_added'),
            release_data.get('instance_id'), release_data.get('folder_id'),
            release_data.get('rating'), release_data.get('notes'),
            release_data.get('condition'), release_data.get('sleeve_condition'),
            marketplace_stats_json, artwork_urls_json, local_artwork_paths_json, raw_data_json,
            
            # For INSERT
            release_data['release_id'], release_data['collection_id'], basic_info_json,
            release_data.get('discogs_id'), release_data.get('title'), release_data.get('artist'),
            release_data.get('year'), release_data.get('label'), release_data.get('catno'),
            release_data.get('format'), genres_json, styles_json, release_data.get('country'),
            release_data.get('date_added'), release_data.get('instance_id'),
            release_data.get('folder_id'), release_data.get('rating'), release_data.get('notes'),
            release_data.get('condition'), release_data.get('sleeve_condition'),
            marketplace_stats_json, artwork_urls_json, local_artwork_paths_json, raw_data_json
        )
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
    
    def upsert_artwork(self, artwork_data: Dict):
        """Insert or update artwork information."""
        query = """
        MERGE INTO ARTWORK a
        USING (SELECT %s as ARTWORK_ID) src
        ON a.ARTWORK_ID = src.ARTWORK_ID
        WHEN MATCHED THEN 
            UPDATE SET LOCAL_FILE_PATH = %s, STAGE_FILE_PATH = %s, FILE_SIZE = %s,
                      IMAGE_WIDTH = %s, IMAGE_HEIGHT = %s, FILE_FORMAT = %s,
                      DOWNLOAD_DATE = %s
        WHEN NOT MATCHED THEN
            INSERT (ARTWORK_ID, RELEASE_ID, IMAGE_TYPE, ORIGINAL_URL, LOCAL_FILE_PATH,
                   STAGE_FILE_PATH, FILE_SIZE, IMAGE_WIDTH, IMAGE_HEIGHT, FILE_FORMAT,
                   DOWNLOAD_DATE)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            # For UPDATE
            artwork_data.get('local_file_path'), artwork_data.get('stage_file_path'),
            artwork_data.get('file_size'), artwork_data.get('image_width'),
            artwork_data.get('image_height'), artwork_data.get('file_format'),
            artwork_data.get('download_date'),
            
            # For INSERT
            artwork_data['artwork_id'], artwork_data['release_id'], artwork_data.get('image_type'),
            artwork_data.get('original_url'), artwork_data.get('local_file_path'),
            artwork_data.get('stage_file_path'), artwork_data.get('file_size'),
            artwork_data.get('image_width'), artwork_data.get('image_height'),
            artwork_data.get('file_format'), artwork_data.get('download_date')
        )
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
    
    def upload_file_to_stage(self, local_file_path: str, stage_file_path: str) -> bool:
        """Upload a file to the Snowflake stage."""
        try:
            query = f"PUT file://{local_file_path} @{self.config.artwork_stage}/{stage_file_path}"
            cursor = self.connection.cursor()
            cursor.execute(query)
            logger.info(f"Uploaded {local_file_path} to stage")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {local_file_path} to stage: {e}")
            return False

class DiscogsCollectionDownloader:
    """Main class for downloading and managing Discogs collection data."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.api = DiscogsAPI(config.token, config.user_agent, config.rate_limit_delay)
        self.artwork_downloader = ArtworkDownloader(config.local_artwork_path)
        self.snowflake = SnowflakeManager(config)
    
    def download_collection(self, download_artwork: bool = True, max_releases: Optional[int] = None):
        """Download complete collection data and artwork."""
        logger.info("Starting Discogs collection download...")
        
        # Connect to Snowflake
        self.snowflake.connect()
        
        try:
            # Get user identity
            identity = self.api.get_user_identity()
            if not identity:
                logger.error("Failed to get user identity")
                return
            
            username = identity['username']
            user_id = str(identity['id'])
            collection_id = f"collection_{user_id}"
            
            logger.info(f"Downloading collection for user: {username}")
            
            # Get collection metadata
            page = 1
            total_items = 0
            release_count = 0
            
            while True:
                collection_page = self.api.get_user_collection(username, page=page)
                if not collection_page:
                    break
                
                # Update collection info on first page
                if page == 1:
                    total_items = collection_page['pagination']['items']
                    collection_data = {
                        'collection_id': collection_id,
                        'user_id': user_id,
                        'username': username,
                        'collection_name': f"{username}'s Collection",
                        'total_items': total_items
                    }
                    self.snowflake.upsert_collection(collection_data)
                    logger.info(f"Collection has {total_items} total items")
                
                # Process releases on this page
                releases = collection_page.get('releases', [])
                for release in releases:
                    if max_releases and release_count >= max_releases:
                        logger.info(f"Reached maximum releases limit: {max_releases}")
                        return
                    
                    self._process_release(collection_id, release, download_artwork)
                    release_count += 1
                    
                    if release_count % 10 == 0:
                        logger.info(f"Processed {release_count}/{total_items} releases")
                
                # Check if we have more pages
                if collection_page['pagination']['page'] >= collection_page['pagination']['pages']:
                    break
                
                page += 1
            
            logger.info(f"Collection download completed! Processed {release_count} releases")
            
        except Exception as e:
            logger.error(f"Error during collection download: {e}")
            raise
        finally:
            self.snowflake.disconnect()
    
    def _process_release(self, collection_id: str, release_data: Dict, download_artwork: bool = True):
        """Process a single release from the collection."""
        try:
            basic_info = release_data.get('basic_information', {})
            release_id = f"release_{release_data.get('id', uuid.uuid4().hex)}"
            
            # Extract basic information
            release_info = {
                'release_id': release_id,
                'collection_id': collection_id,
                'basic_information': basic_info,
                'discogs_id': basic_info.get('id'),
                'title': basic_info.get('title'),
                'artist': ', '.join([artist.get('name', '') for artist in basic_info.get('artists', [])]),
                'year': basic_info.get('year'),
                'label': ', '.join([label.get('name', '') for label in basic_info.get('labels', [])]),
                'catno': ', '.join([label.get('catno', '') for label in basic_info.get('labels', [])]),
                'format': ', '.join([fmt.get('name', '') for fmt in basic_info.get('formats', [])]),
                'genres': basic_info.get('genres', []),
                'styles': basic_info.get('styles', []),
                'country': basic_info.get('country'),
                'date_added': release_data.get('date_added'),
                'instance_id': release_data.get('instance_id'),
                'folder_id': release_data.get('folder_id'),
                'rating': release_data.get('rating'),
                'notes': release_data.get('notes', {}).get('value'),
                'condition': release_data.get('condition'),
                'sleeve_condition': release_data.get('sleeve_condition'),
                'marketplace_stats': {},
                'artwork_urls': [],
                'local_artwork_paths': [],
                'raw_data': release_data
            }
            
            # Download artwork if requested
            if download_artwork and basic_info.get('thumb'):
                artwork_urls = [basic_info['thumb']]
                
                # Get additional images from detailed release info
                detailed_release = self.api.get_release_details(basic_info.get('id'))
                if detailed_release and detailed_release.get('images'):
                    artwork_urls.extend([img['uri'] for img in detailed_release['images']])
                
                release_info['artwork_urls'] = artwork_urls
                
                # Download each image
                local_paths = []
                for i, image_url in enumerate(artwork_urls):
                    image_type = "primary" if i == 0 else f"image_{i}"
                    result = self.artwork_downloader.download_image(image_url, release_id, image_type)
                    
                    if result:
                        local_file_path, metadata = result
                        local_paths.append(local_file_path)
                        
                        # Create artwork record
                        artwork_data = {
                            'artwork_id': f"artwork_{release_id}_{i}",
                            'release_id': release_id,
                            'image_type': image_type,
                            'original_url': image_url,
                            **metadata
                        }
                        
                        # Upload to Snowflake stage
                        stage_path = f"{release_id}/{Path(local_file_path).name}"
                        if self.snowflake.upload_file_to_stage(local_file_path, stage_path):
                            artwork_data['stage_file_path'] = stage_path
                        
                        self.snowflake.upsert_artwork(artwork_data)
                
                release_info['local_artwork_paths'] = local_paths
            
            # Save release to database
            self.snowflake.upsert_release(release_info)
            
        except Exception as e:
            logger.error(f"Error processing release {release_data.get('id', 'unknown')}: {e}")

def load_config() -> DiscogsConfig:
    """Load configuration from environment variables or config file."""
    # Try to load from environment variables
    token = os.getenv('DISCOGS_TOKEN')
    user_agent = os.getenv('DISCOGS_USER_AGENT', 'DiscogsCollectionDownloader/1.0')
    
    snowflake_account = os.getenv('SNOWFLAKE_ACCOUNT')
    snowflake_user = os.getenv('SNOWFLAKE_USER')
    snowflake_password = os.getenv('SNOWFLAKE_PASSWORD')
    snowflake_warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
    
    if not all([token, snowflake_account, snowflake_user, snowflake_password, snowflake_warehouse]):
        # Try to load from config file
        config_file = Path('discogs_config.json')
        if config_file.exists():
            with open(config_file) as f:
                config_data = json.load(f)
            
            return DiscogsConfig(**config_data)
        else:
            print("Configuration not found. Please set environment variables or create discogs_config.json")
            print("Required environment variables:")
            print("- DISCOGS_TOKEN")
            print("- DISCOGS_USER_AGENT (optional)")
            print("- SNOWFLAKE_ACCOUNT")
            print("- SNOWFLAKE_USER") 
            print("- SNOWFLAKE_PASSWORD")
            print("- SNOWFLAKE_WAREHOUSE")
            sys.exit(1)
    
    return DiscogsConfig(
        token=token,
        user_agent=user_agent,
        snowflake_account=snowflake_account,
        snowflake_user=snowflake_user,
        snowflake_password=snowflake_password,
        snowflake_warehouse=snowflake_warehouse
    )

def main():
    """Main entry point for the downloader."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download Discogs collection data and artwork')
    parser.add_argument('--no-artwork', action='store_true', help='Skip artwork download')
    parser.add_argument('--max-releases', type=int, help='Maximum number of releases to process')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Create downloader instance
    downloader = DiscogsCollectionDownloader(config)
    
    # Start download
    try:
        downloader.download_collection(
            download_artwork=not args.no_artwork,
            max_releases=args.max_releases
        )
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()