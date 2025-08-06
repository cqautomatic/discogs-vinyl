#!/usr/bin/env python3
"""
Discogs Collection Downloader (PostgreSQL Version)
Downloads collection data and artwork from Discogs API and stores in PostgreSQL.
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
import psycopg2
import psycopg2.extras
from psycopg2 import sql
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
    """Configuration for Discogs API and PostgreSQL connection."""
    token: str
    user_agent: str
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_database: str
    postgres_schema: str = "collection_data"
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
    """Handles downloading and managing artwork files with robust retry logic."""
    
    def __init__(self, local_path: str = "./artwork"):
        self.local_path = Path(local_path)
        self.local_path.mkdir(parents=True, exist_ok=True)
        self.session = self._create_session()
        
        # Configuration
        self.max_retries = 5
        self.base_retry_delay = 2.0
        self.max_retry_delay = 60.0
        self.jitter_percent = 0.2
        self.timeout = 30
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'DiscogsCollectionDownloader/1.0',
            'Accept': 'image/jpeg,image/png,image/gif,image/webp,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        return session
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        import random
        
        # Exponential backoff
        delay = self.base_retry_delay * (2 ** attempt)
        delay = min(delay, self.max_retry_delay)
        
        # Add jitter
        jitter = delay * self.jitter_percent * (2 * random.random() - 1)
        final_delay = delay + jitter
        
        return max(final_delay, 0.1)
    
    def _file_exists_and_valid(self, file_path: Path) -> bool:
        """Check if file exists and has valid size."""
        if not file_path.exists():
            return False
        try:
            file_size = file_path.stat().st_size
            return file_size > 1024  # At least 1KB
        except OSError:
            return False
    
    def download_image(self, image_url: str, release_id: str, image_type: str = "primary") -> Optional[Tuple[str, Dict]]:
        """Download an image with retry logic and return local path and metadata."""
        if not image_url or not image_url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid image URL: {image_url}")
            return None
        
        # Generate filename based on URL hash and release ID
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        file_extension = image_url.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            file_extension = 'jpg'
        
        filename = f"{release_id}_{image_type}_{url_hash}.{file_extension}"
        local_file_path = self.local_path / filename
        
        # Check if file already exists
        if self._file_exists_and_valid(local_file_path):
            logger.debug(f"Image already exists: {filename}")
            return self._get_file_metadata(local_file_path, image_url)
        
        # Attempt download with retries
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {image_url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.get(image_url, stream=True, timeout=self.timeout)
                
                if response.status_code == 404:
                    logger.warning(f"Image not found (404): {image_url}")
                    return None
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403): {image_url}")
                    return None
                elif response.status_code != 200:
                    raise requests.RequestException(f"HTTP {response.status_code}")
                
                # Validate content type
                content_type = response.headers.get('content-type', '').lower()
                if content_type and not content_type.startswith('image/'):
                    logger.warning(f"Invalid content type: {content_type}")
                    return None
                
                # Download the file
                temp_file_path = local_file_path.with_suffix(f"{local_file_path.suffix}.tmp")
                bytes_downloaded = 0
                
                with open(temp_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                
                if bytes_downloaded == 0:
                    temp_file_path.unlink(missing_ok=True)
                    raise ValueError("Downloaded file is empty")
                
                # Move temp file to final location
                temp_file_path.rename(local_file_path)
                
                logger.info(f"Successfully downloaded: {filename} ({bytes_downloaded} bytes)")
                return self._get_file_metadata(local_file_path, image_url)
                
            except (requests.RequestException, OSError, ValueError) as e:
                last_exception = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                
                # Clean up temp file
                temp_file_path = local_file_path.with_suffix(f"{local_file_path.suffix}.tmp")
                temp_file_path.unlink(missing_ok=True)
                
                # Wait before retrying
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"Waiting {delay:.2f} seconds before retry...")
                    time.sleep(delay)
            
            except Exception as e:
                logger.error(f"Unexpected error downloading {image_url}: {e}")
                return None
        
        # All retries failed
        logger.error(f"Failed to download {image_url} after {self.max_retries} attempts. Last error: {last_exception}")
        return None
    
    def _get_file_metadata(self, file_path: Path, original_url: str) -> Tuple[str, Dict]:
        """Get metadata for a downloaded file."""
        try:
            stat = file_path.stat()
            file_size = stat.st_size
            
            # Try to get image dimensions
            width, height = None, None
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    width, height = img.size
            except ImportError:
                logger.debug("PIL not available for image dimension detection")
            except Exception as e:
                logger.debug(f"Could not get image dimensions: {e}")
            
            metadata = {
                'local_file_path': str(file_path),
                'file_size': file_size,
                'image_width': width,
                'image_height': height,
                'file_format': file_path.suffix[1:].lower(),
                'download_date': datetime.now(),
                'original_url': original_url
            }
            
            return str(file_path), metadata
            
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return str(file_path), {'local_file_path': str(file_path), 'original_url': original_url}

class PostgreSQLManager:
    """Manages PostgreSQL database operations."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.connection = None
    
    def connect(self):
        """Establish connection to PostgreSQL."""
        try:
            self.connection = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password
            )
            self.connection.autocommit = False
            
            # Set search path to our schema
            with self.connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {self.config.postgres_schema}, public")
            self.connection.commit()
            
            logger.info("Connected to PostgreSQL successfully")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def disconnect(self):
        """Close PostgreSQL connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """Execute a query and return results."""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    def upsert_collection(self, collection_data: Dict):
        """Insert or update collection information."""
        query = """
        INSERT INTO collections (collection_id, user_id, username, collection_name, total_items)
        VALUES (%(collection_id)s, %(user_id)s, %(username)s, %(collection_name)s, %(total_items)s)
        ON CONFLICT (collection_id) 
        DO UPDATE SET 
            user_id = EXCLUDED.user_id,
            username = EXCLUDED.username,
            collection_name = EXCLUDED.collection_name,
            total_items = EXCLUDED.total_items,
            last_updated = CURRENT_TIMESTAMP
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, collection_data)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error upserting collection: {e}")
            self.connection.rollback()
            raise
    
    def upsert_release(self, release_data: Dict):
        """Insert or update release information."""
        query = """
        INSERT INTO releases (
            release_id, collection_id, basic_information, discogs_id, title, artist, year,
            label, catno, format, genres, styles, country, date_added, instance_id,
            folder_id, rating, notes, condition, sleeve_condition, marketplace_stats,
            artwork_urls, local_artwork_paths, raw_data
        ) VALUES (
            %(release_id)s, %(collection_id)s, %(basic_information)s, %(discogs_id)s, 
            %(title)s, %(artist)s, %(year)s, %(label)s, %(catno)s, %(format)s,
            %(genres)s, %(styles)s, %(country)s, %(date_added)s, %(instance_id)s,
            %(folder_id)s, %(rating)s, %(notes)s, %(condition)s, %(sleeve_condition)s,
            %(marketplace_stats)s, %(artwork_urls)s, %(local_artwork_paths)s, %(raw_data)s
        )
        ON CONFLICT (release_id)
        DO UPDATE SET
            basic_information = EXCLUDED.basic_information,
            discogs_id = EXCLUDED.discogs_id,
            title = EXCLUDED.title,
            artist = EXCLUDED.artist,
            year = EXCLUDED.year,
            label = EXCLUDED.label,
            catno = EXCLUDED.catno,
            format = EXCLUDED.format,
            genres = EXCLUDED.genres,
            styles = EXCLUDED.styles,
            country = EXCLUDED.country,
            date_added = EXCLUDED.date_added,
            instance_id = EXCLUDED.instance_id,
            folder_id = EXCLUDED.folder_id,
            rating = EXCLUDED.rating,
            notes = EXCLUDED.notes,
            condition = EXCLUDED.condition,
            sleeve_condition = EXCLUDED.sleeve_condition,
            marketplace_stats = EXCLUDED.marketplace_stats,
            artwork_urls = EXCLUDED.artwork_urls,
            local_artwork_paths = EXCLUDED.local_artwork_paths,
            raw_data = EXCLUDED.raw_data,
            last_updated = CURRENT_TIMESTAMP
        """
        
        # Convert lists to JSON for PostgreSQL JSONB columns
        processed_data = release_data.copy()
        for json_field in ['basic_information', 'genres', 'styles', 'marketplace_stats', 
                          'artwork_urls', 'local_artwork_paths', 'raw_data']:
            if json_field in processed_data and processed_data[json_field] is not None:
                if not isinstance(processed_data[json_field], str):
                    processed_data[json_field] = json.dumps(processed_data[json_field])
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, processed_data)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error upserting release: {e}")
            self.connection.rollback()
            raise
    
    def upsert_artwork(self, artwork_data: Dict):
        """Insert or update artwork information."""
        query = """
        INSERT INTO artwork (
            artwork_id, release_id, image_type, original_url, local_file_path,
            file_size, image_width, image_height, file_format, download_date
        ) VALUES (
            %(artwork_id)s, %(release_id)s, %(image_type)s, %(original_url)s,
            %(local_file_path)s, %(file_size)s, %(image_width)s, %(image_height)s,
            %(file_format)s, %(download_date)s
        )
        ON CONFLICT (artwork_id)
        DO UPDATE SET
            local_file_path = EXCLUDED.local_file_path,
            file_size = EXCLUDED.file_size,
            image_width = EXCLUDED.image_width,
            image_height = EXCLUDED.image_height,
            file_format = EXCLUDED.file_format,
            download_date = EXCLUDED.download_date
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, artwork_data)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error upserting artwork: {e}")
            self.connection.rollback()
            raise

class DiscogsCollectionDownloader:
    """Main class for downloading and managing Discogs collection data."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.api = DiscogsAPI(config.token, config.user_agent, config.rate_limit_delay)
        self.artwork_downloader = ArtworkDownloader(config.local_artwork_path)
        self.postgres = PostgreSQLManager(config)
    
    def download_collection(self, download_artwork: bool = True, max_releases: Optional[int] = None):
        """Download complete collection data and artwork."""
        logger.info("Starting Discogs collection download...")
        
        # Connect to PostgreSQL
        self.postgres.connect()
        
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
                    self.postgres.upsert_collection(collection_data)
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
            self.postgres.disconnect()
    
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
                'notes': release_data.get('notes', {}).get('value') if release_data.get('notes') else None,
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
                        
                        self.postgres.upsert_artwork(artwork_data)
                
                release_info['local_artwork_paths'] = local_paths
            
            # Save release to database
            self.postgres.upsert_release(release_info)
            
        except Exception as e:
            logger.error(f"Error processing release {release_data.get('id', 'unknown')}: {e}")

class PhotosOnlyDownloader:
    """Downloads only missing photos for existing releases in the database."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.postgres = PostgreSQLManager(config)
        self.artwork_downloader = ArtworkDownloader(config.local_artwork_path)
        
    def get_releases_without_artwork(self) -> List[Tuple[str, List[str]]]:
        """Get releases that don't have downloaded artwork."""
        query = """
        SELECT DISTINCT r.release_id, r.artwork_urls
        FROM collection_data.releases r
        LEFT JOIN collection_data.artwork a ON r.release_id = a.release_id
        WHERE r.artwork_urls IS NOT NULL 
        AND r.artwork_urls != '[]'
        AND a.release_id IS NULL
        ORDER BY r.release_id
        """
        
        with self.postgres.connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        
        releases_to_download = []
        for release_id, artwork_urls_json in results:
            if artwork_urls_json:
                try:
                    import json
                    artwork_urls = json.loads(artwork_urls_json) if isinstance(artwork_urls_json, str) else artwork_urls_json
                    if artwork_urls:
                        releases_to_download.append((release_id, artwork_urls))
                except Exception as e:
                    logger.warning(f"Could not parse artwork URLs for release {release_id}: {e}")
        
        return releases_to_download
    
    def download_missing_photos(self, force_redownload: bool = False, max_releases: Optional[int] = None):
        """Download missing photos for releases."""
        # Connect to database
        self.postgres.connect()
        
        try:
            releases_to_download = self.get_releases_without_artwork()
            
            if max_releases:
                releases_to_download = releases_to_download[:max_releases]
            
            logger.info(f"Found {len(releases_to_download)} releases without artwork")
            
            for i, (release_id, artwork_urls) in enumerate(releases_to_download, 1):
                logger.info(f"Processing release {i}/{len(releases_to_download)}: {release_id}")
                
                try:
                    # Download each image
                    for j, image_url in enumerate(artwork_urls):
                        if not image_url:
                            continue
                            
                        image_type = "primary" if j == 0 else f"image_{j}"
                        
                        # Check if already exists (unless force redownload)
                        if not force_redownload:
                            existing_check = """
                            SELECT artwork_id FROM collection_data.artwork 
                            WHERE release_id = %s AND image_type = %s AND original_url = %s
                            """
                            with self.postgres.connection.cursor() as cursor:
                                cursor.execute(existing_check, (release_id, image_type, image_url))
                                if cursor.fetchone():
                                    logger.debug(f"Artwork already exists in DB: {release_id}_{image_type}")
                                    continue
                        
                        # Download the image
                        result = self.artwork_downloader.download_image(image_url, release_id, image_type)
                        
                        if result:
                            local_file_path, metadata = result
                            
                            # Create artwork record
                            artwork_data = {
                                'artwork_id': f"artwork_{release_id}_{j}",
                                'release_id': release_id,
                                'image_type': image_type,
                                **metadata
                            }
                            
                            self.postgres.upsert_artwork(artwork_data)
                            logger.info(f"Saved artwork to DB: {artwork_data['artwork_id']}")
                        
                        # Rate limiting
                        time.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error processing release {release_id}: {e}")
                    
        finally:
            if self.postgres.connection:
                self.postgres.connection.close()

def load_config() -> DiscogsConfig:
    """Load configuration from environment variables or config file."""
    # Try to load from environment variables
    token = os.getenv('DISCOGS_TOKEN')
    user_agent = os.getenv('DISCOGS_USER_AGENT', 'DiscogsCollectionDownloader/1.0')
    
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
    postgres_user = os.getenv('POSTGRES_USER')
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    postgres_database = os.getenv('POSTGRES_DATABASE', 'discogs_collection')
    
    if not all([token, postgres_user, postgres_password]):
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
            print("- POSTGRES_HOST (default: localhost)")
            print("- POSTGRES_PORT (default: 5432)")
            print("- POSTGRES_USER") 
            print("- POSTGRES_PASSWORD")
            print("- POSTGRES_DATABASE (default: discogs_collection)")
            sys.exit(1)
    
    return DiscogsConfig(
        token=token,
        user_agent=user_agent,
        postgres_host=postgres_host,
        postgres_port=postgres_port,
        postgres_user=postgres_user,
        postgres_password=postgres_password,
        postgres_database=postgres_database
    )

def main():
    """Main entry point for the downloader."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download Discogs collection data and artwork')
    parser.add_argument('--no-artwork', action='store_true', help='Skip artwork download')
    parser.add_argument('--photos-only', action='store_true', 
                       help='Only download missing photos for existing releases (skip collection data)')
    parser.add_argument('--force-redownload-photos', action='store_true',
                       help='Redownload existing photos (use with --photos-only)')
    parser.add_argument('--max-releases', type=int, help='Maximum number of releases to process')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if args.photos_only:
        # Photos-only mode: download missing artwork for existing releases
        logger.info("Running in photos-only mode")
        try:
            photos_downloader = PhotosOnlyDownloader(config)
            photos_downloader.download_missing_photos(
                force_redownload=args.force_redownload_photos,
                max_releases=args.max_releases
            )
        except Exception as e:
            logger.error(f"Photos-only download failed: {e}")
            sys.exit(1)
    else:
        # Normal mode: download collection data and artwork
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