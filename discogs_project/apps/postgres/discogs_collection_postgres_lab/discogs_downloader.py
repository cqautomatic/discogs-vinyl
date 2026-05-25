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
import os

# TOML loader (Python 3.11+: tomllib; else optional tomli)
try:
    import tomllib as tomli  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    try:
        import tomli  # type: ignore
    except Exception:
        tomli = None  # type: ignore

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

# Robust data extraction functions to handle unexpected Discogs API responses
def safe_get_name(item, field_name='name', default=''):
    """Safely extract a name field from an item that might be a dict, list, or string."""
    try:
        if isinstance(item, dict):
            return item.get(field_name, default)
        elif isinstance(item, str):
            return item
        elif isinstance(item, list):
            if len(item) > 0 and isinstance(item[0], dict):
                return item[0].get(field_name, default)
            elif len(item) > 0 and isinstance(item[0], str):
                return item[0]
            else:
                return default
        elif item is None:
            return default
        else:
            return str(item)
    except Exception as e:
        logger.debug(f"Error extracting {field_name} from {type(item)}: {e}")
        return default

def safe_extract_artists(artists_data):
    """Safely extract artist names from artists data."""
    if not artists_data:
        return ''
    try:
        if isinstance(artists_data, list):
            names = []
            for artist in artists_data:
                name = safe_get_name(artist, 'name', '')
                if name:
                    names.append(name)
            return ', '.join(names)
        elif isinstance(artists_data, dict):
            return safe_get_name(artists_data, 'name', '')
        elif isinstance(artists_data, str):
            return artists_data
        else:
            return str(artists_data)
    except Exception as e:
        logger.warning(f"Error extracting artists: {e}")
        return ''

def safe_extract_labels(labels_data):
    """Safely extract label names from labels data."""
    if not labels_data:
        return ''
    try:
        if isinstance(labels_data, list):
            names = []
            for label in labels_data:
                name = safe_get_name(label, 'name', '')
                if name:
                    names.append(name)
            return ', '.join(names)
        elif isinstance(labels_data, dict):
            return safe_get_name(labels_data, 'name', '')
        elif isinstance(labels_data, str):
            return labels_data
        else:
            return str(labels_data)
    except Exception as e:
        logger.warning(f"Error extracting labels: {e}")
        return ''

def safe_extract_catalog_numbers(labels_data):
    """Safely extract catalog numbers from labels data."""
    if not labels_data:
        return ''
    try:
        if isinstance(labels_data, list):
            catnos = []
            for label in labels_data:
                catno = safe_get_name(label, 'catno', '')
                if catno:
                    catnos.append(catno)
            return ', '.join(catnos)
        elif isinstance(labels_data, dict):
            return safe_get_name(labels_data, 'catno', '')
        elif isinstance(labels_data, str):
            return labels_data
        else:
            return ''
    except Exception as e:
        logger.warning(f"Error extracting catalog numbers: {e}")
        return ''

def safe_extract_formats(formats_data):
    """Safely extract format names from formats data."""
    if not formats_data:
        return ''
    try:
        if isinstance(formats_data, list):
            names = []
            for fmt in formats_data:
                name = safe_get_name(fmt, 'name', '')
                if name:
                    names.append(name)
            return ', '.join(names)
        elif isinstance(formats_data, dict):
            return safe_get_name(formats_data, 'name', '')
        elif isinstance(formats_data, str):
            return formats_data
        else:
            return str(formats_data)
    except Exception as e:
        logger.warning(f"Error extracting formats: {e}")
        return ''

def safe_extract_list_field(data, default=None):
    """Safely extract a field that should be a list."""
    if default is None:
        default = []
    try:
        if isinstance(data, list):
            return data
        elif isinstance(data, str):
            return [data] if data else default
        elif data is None:
            return default
        else:
            return [str(data)]
    except Exception as e:
        logger.debug(f"Error extracting list field: {e}")
        return default

def safe_extract_notes(notes_data):
    """Safely extract notes value from notes data."""
    if not notes_data:
        return None
    try:
        if isinstance(notes_data, dict):
            return notes_data.get('value', None)
        elif isinstance(notes_data, str):
            return notes_data
        elif isinstance(notes_data, list):
            if len(notes_data) > 0:
                if isinstance(notes_data[0], dict):
                    return notes_data[0].get('value', None)
                else:
                    return str(notes_data[0])
            return None
        else:
            return str(notes_data)
    except Exception as e:
        logger.debug(f"Error extracting notes: {e}")
        return None

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
    username: Optional[str] = None  # Optional username override
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
    
    def get_release_statistics(self, release_id: int) -> Optional[Dict]:
        """Get release statistics including have/want counts, ratings, and marketplace data.
        
        Note: Historical sales data (last sold date, high/low sale prices) is not available
        via public API. Only current marketplace listings are accessible.
        """
        try:
            # Get basic release info with community stats
            release_data = self.get_release_details(release_id)
            if not release_data:
                return None
            
            # Extract community statistics
            community = release_data.get('community', {})
            rating_data = community.get('rating', {})
            
            stats = {
                'have_count': community.get('have', 0),
                'want_count': community.get('want', 0),
                'rating_count': rating_data.get('count', 0),
                'average_rating': rating_data.get('average', 0.0),
                'community_status': community.get('status', 'Unknown'),
                'data_quality': community.get('data_quality', 'Unknown'),
                'contributors_count': len(community.get('contributors', [])),
                'marketplace_stats': {}
            }
            
            # Get marketplace statistics
            try:
                marketplace_data = self._make_request(f"/marketplace/stats/{release_id}")
                if marketplace_data:
                    stats['marketplace_stats'] = {
                        'num_for_sale': marketplace_data.get('num_for_sale', 0),
                        'lowest_price': marketplace_data.get('lowest_price', {}),
                        'blocked_from_sale': marketplace_data.get('blocked_from_sale', False)
                    }
            except Exception as e:
                logger.debug(f"Could not fetch marketplace stats for release {release_id}: {e}")
                stats['marketplace_stats'] = {}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching release statistics for {release_id}: {e}")
            return None

    def get_marketplace_stats(self, release_id: int) -> Optional[Dict]:
        """Get current marketplace stats for a release (for sale count, lowest listing price).

        Note: Historical sales (last sold date, high/low sold prices) are not available via public API.
        """
        try:
            data = self._make_request(f"/marketplace/stats/{release_id}")
            return data
        except Exception as e:
            logger.debug(f"Could not fetch marketplace stats for release {release_id}: {e}")
            return None
    
    def get_master_release(self, master_id: int) -> Optional[Dict]:
        """Get master release information."""
        return self._make_request(f"/masters/{master_id}")
    
    def get_artist_details(self, artist_id: int) -> Optional[Dict]:
        """Get detailed artist information."""
        return self._make_request(f"/artists/{artist_id}")
    
    def get_label_details(self, label_id: int) -> Optional[Dict]:
        """Get detailed label information."""
        return self._make_request(f"/labels/{label_id}")

    def get_user_wantlist(self, username: str, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Get user's wantlist (wishlist)."""
        return self._make_request(f"/users/{username}/wants", {'page': page, 'per_page': per_page})

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
    
    def get_image_urls_from_discogs_data(self, image_data: Dict) -> Tuple[str, str]:
        """Extract full-size and thumbnail URLs from Discogs image data."""
        # Discogs API provides 'uri' (600x600) and 'uri150' (150x150)
        full_size_url = image_data.get('uri', '')  # 600x600 is the "full size" from Discogs
        thumbnail_url = image_data.get('uri150', '')  # 150x150 thumbnail
        
        # Fallback: if uri150 doesn't exist, use uri for both
        if not thumbnail_url and full_size_url:
            thumbnail_url = full_size_url
        
        return full_size_url, thumbnail_url
    
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
    
    def download_image(self, image_url: str, release_id: str, image_type: str = "primary", download_thumbnail: bool = True, image_data: Dict = None) -> Optional[Tuple[str, Dict]]:
        """Download an image with retry logic and return local path and metadata."""
        # Initialize local_file_path to None to avoid UnboundLocalError
        local_file_path = None
        thumbnail_file_path = None
        
        if not image_url or not image_url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid image URL: {image_url}")
            return None
        
        # Get full-size and thumbnail URLs
        if image_data:
            # Use the proper Discogs image data to get both sizes
            full_size_url, thumbnail_url = self.get_image_urls_from_discogs_data(image_data)
        else:
            # Fallback: assume the provided URL is the full-size one
            full_size_url = image_url
            thumbnail_url = image_url if download_thumbnail else None
        
        # Generate filename based on URL hash and release ID
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        file_extension = image_url.split('.')[-1].lower()
        if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            file_extension = 'jpg'
        
        filename = f"{release_id}_{image_type}_{url_hash}.{file_extension}"
        thumb_filename = f"{release_id}_{image_type}_{url_hash}_thumb.{file_extension}"
        local_file_path = self.local_path / filename
        thumbnail_file_path = self.local_path / thumb_filename if download_thumbnail else None
        
        # Check if files already exist
        full_exists = self._file_exists_and_valid(local_file_path)
        thumb_exists = thumbnail_file_path and self._file_exists_and_valid(thumbnail_file_path)
        
        if full_exists and (not download_thumbnail or thumb_exists):
            logger.debug(f"Images already exist: {filename}")
            return self._get_file_metadata(local_file_path, image_url, thumbnail_file_path)
        
        # Download full-size image first
        if not full_exists:
            success = self._download_single_image(full_size_url, local_file_path, f"full-size {filename}")
            if not success:
                return None
        
        # Download thumbnail if requested and doesn't exist
        if download_thumbnail and thumbnail_file_path and not thumb_exists:
            success = self._download_single_image(thumbnail_url, thumbnail_file_path, f"thumbnail {thumb_filename}")
            # Don't fail if thumbnail download fails - we still have the full-size image
            if not success:
                logger.warning(f"Thumbnail download failed for {thumb_filename}, but full-size succeeded")
        
        return self._get_file_metadata(local_file_path, image_url, thumbnail_file_path)
    
    def _download_single_image(self, image_url: str, file_path: Path, description: str) -> bool:
        """Download a single image file with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {description} from {image_url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.get(image_url, stream=True, timeout=self.timeout)
                
                if response.status_code == 404:
                    logger.warning(f"Image not found (404): {image_url}")
                    return False
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403): {image_url}")
                    return False
                elif response.status_code != 200:
                    raise requests.RequestException(f"HTTP {response.status_code}")
                
                # Validate content type
                content_type = response.headers.get('content-type', '').lower()
                if content_type and not content_type.startswith('image/'):
                    logger.warning(f"Invalid content type: {content_type}")
                    return False
                
                # Download the file
                temp_file_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
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
                temp_file_path.rename(file_path)
                
                logger.info(f"Successfully downloaded {description}: ({bytes_downloaded} bytes)")
                return True
                
            except (requests.RequestException, OSError, ValueError) as e:
                last_exception = e
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                
                # Clean up temp file
                temp_file_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
                temp_file_path.unlink(missing_ok=True)
                
                # Wait before retrying
                if attempt < self.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"Waiting {delay:.2f} seconds before retry...")
                    time.sleep(delay)
            
            except Exception as e:
                logger.error(f"Unexpected error downloading {image_url}: {e}")
                return False
        
        # All retries failed
        logger.error(f"Failed to download {image_url} after {self.max_retries} attempts. Last error: {last_exception}")
        return False
    
    def _get_file_metadata(self, file_path: Path, original_url: str, thumbnail_path: Path = None) -> Tuple[str, Dict]:
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
                'thumbnail_file_path': str(thumbnail_path) if thumbnail_path else None,
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
            label, catno, format, genres, styles, copies_count, instance_ids, producers, country, date_added, instance_id,
            folder_id, rating, notes, condition, sleeve_condition, marketplace_stats,
            artwork_urls, local_artwork_paths, community_have_count, community_want_count, 
            community_rating_count, community_average_rating, stats_last_updated, raw_data
        ) VALUES (
            %(release_id)s, %(collection_id)s, %(basic_information)s, %(discogs_id)s, 
            %(title)s, %(artist)s, %(year)s, %(label)s, %(catno)s, %(format)s,
            %(genres)s, %(styles)s, %(copies_count)s, %(instance_ids)s, %(producers)s, %(country)s, %(date_added)s, %(instance_id)s,
            %(folder_id)s, %(rating)s, %(notes)s, %(condition)s, %(sleeve_condition)s,
            %(marketplace_stats)s, %(artwork_urls)s, %(local_artwork_paths)s, %(community_have_count)s, %(community_want_count)s,
            %(community_rating_count)s, %(community_average_rating)s, %(stats_last_updated)s, %(raw_data)s
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
            copies_count = EXCLUDED.copies_count,
            instance_ids = EXCLUDED.instance_ids,
            producers = EXCLUDED.producers,
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
            community_have_count = EXCLUDED.community_have_count,
            community_want_count = EXCLUDED.community_want_count,
            community_rating_count = EXCLUDED.community_rating_count,
            community_average_rating = EXCLUDED.community_average_rating,
            stats_last_updated = EXCLUDED.stats_last_updated,
            raw_data = EXCLUDED.raw_data,
            last_updated = CURRENT_TIMESTAMP
        """
        
        # Convert lists to JSON for PostgreSQL JSONB columns
        processed_data = release_data.copy()
        for json_field in ['basic_information', 'genres', 'styles', 'instance_ids', 'producers', 'marketplace_stats', 
                          'artwork_urls', 'local_artwork_paths', 'raw_data']:
            if json_field in processed_data and processed_data[json_field] is not None:
                if not isinstance(processed_data[json_field], str):
                    processed_data[json_field] = json.dumps(processed_data[json_field])
        
        # Ensure community statistics fields have default values if not provided
        processed_data.setdefault('community_have_count', 0)
        processed_data.setdefault('community_want_count', 0)
        processed_data.setdefault('community_rating_count', 0)
        processed_data.setdefault('community_average_rating', 0.0)
        processed_data.setdefault('stats_last_updated', None)
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, processed_data)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error upserting release: {e}")
            self.connection.rollback()
            raise
    
    def upsert_artwork(self, artwork_data: Dict):
        """Insert or update artwork information with robust error handling."""
        # Validate that release_id exists first
        release_check_query = "SELECT 1 FROM releases WHERE release_id = %(release_id)s"
        
        query = """
        INSERT INTO artwork (
            artwork_id, release_id, image_type, original_url, local_file_path,
            thumbnail_file_path, file_size, image_width, image_height, file_format, download_date
        ) VALUES (
            %(artwork_id)s, %(release_id)s, %(image_type)s, %(original_url)s,
            %(local_file_path)s, %(thumbnail_file_path)s, %(file_size)s, %(image_width)s, %(image_height)s,
            %(file_format)s, %(download_date)s
        )
        ON CONFLICT (artwork_id)
        DO UPDATE SET
            local_file_path = EXCLUDED.local_file_path,
            thumbnail_file_path = EXCLUDED.thumbnail_file_path,
            file_size = EXCLUDED.file_size,
            image_width = EXCLUDED.image_width,
            image_height = EXCLUDED.image_height,
            file_format = EXCLUDED.file_format,
            download_date = EXCLUDED.download_date
        """
        
        try:
            with self.connection.cursor() as cursor:
                # First verify the release exists
                cursor.execute(release_check_query, {'release_id': artwork_data['release_id']})
                if not cursor.fetchone():
                    raise ValueError(f"Release {artwork_data['release_id']} does not exist - cannot insert artwork")
                
                # Insert/update the artwork
                cursor.execute(query, artwork_data)
            self.connection.commit()
            
        except psycopg2.IntegrityError as e:
            logger.error(f"Foreign key constraint violation for artwork {artwork_data.get('artwork_id', 'unknown')}: {e}")
            self.connection.rollback()
            raise
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error upserting artwork {artwork_data.get('artwork_id', 'unknown')}: {e}")
            self.connection.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error upserting artwork {artwork_data.get('artwork_id', 'unknown')}: {e}")
            self.connection.rollback()
            raise
    
    def upsert_track(self, track_data: Dict):
        """Insert or update track information."""
        query = """
        INSERT INTO tracks (
            track_id, release_id, track_number, title, duration, artists, extraartists, raw_track_data
        ) VALUES (
            %(track_id)s, %(release_id)s, %(track_number)s, %(title)s, %(duration)s,
            %(artists)s, %(extraartists)s, %(raw_track_data)s
        )
        ON CONFLICT (track_id)
        DO UPDATE SET
            track_number = EXCLUDED.track_number,
            title = EXCLUDED.title,
            duration = EXCLUDED.duration,
            artists = EXCLUDED.artists,
            extraartists = EXCLUDED.extraartists,
            raw_track_data = EXCLUDED.raw_track_data
        """
        
        # Convert lists to JSON for PostgreSQL JSONB columns
        processed_data = track_data.copy()
        for json_field in ['artists', 'extraartists', 'raw_track_data']:
            if json_field in processed_data and processed_data[json_field] is not None:
                if not isinstance(processed_data[json_field], str):
                    processed_data[json_field] = json.dumps(processed_data[json_field])
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, processed_data)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error upserting track: {e}")
            self.connection.rollback()
            raise
    
    def upsert_artist_discography(self, discography_data: Dict):
        """Insert or update artist discography information."""
        query = """
        INSERT INTO artist_discography (
            discography_id, artist_id, discogs_artist_id, artist_name, release_id,
            discogs_release_id, title, year, role, label, format, country,
            in_collection, collection_release_id, raw_data
        ) VALUES (
            %(discography_id)s, %(artist_id)s, %(discogs_artist_id)s, %(artist_name)s,
            %(release_id)s, %(discogs_release_id)s, %(title)s, %(year)s, %(role)s,
            %(label)s, %(format)s, %(country)s, %(in_collection)s, %(collection_release_id)s,
            %(raw_data)s
        )
        ON CONFLICT (discography_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            year = EXCLUDED.year,
            role = EXCLUDED.role,
            label = EXCLUDED.label,
            format = EXCLUDED.format,
            country = EXCLUDED.country,
            in_collection = EXCLUDED.in_collection,
            collection_release_id = EXCLUDED.collection_release_id,
            raw_data = EXCLUDED.raw_data
        """
        
        # Convert to JSON if needed
        processed_data = discography_data.copy()
        if 'raw_data' in processed_data and processed_data['raw_data'] is not None:
            if not isinstance(processed_data['raw_data'], str):
                processed_data['raw_data'] = json.dumps(processed_data['raw_data'])
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, processed_data)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error upserting artist discography: {e}")
            self.connection.rollback()
            raise

class DiscogsCollectionDownloader:
    """Main class for downloading and managing Discogs collection data."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.api = DiscogsAPI(config.token, config.user_agent, config.rate_limit_delay)
        self.artwork_downloader = ArtworkDownloader(config.local_artwork_path)
        self.postgres = PostgreSQLManager(config)
    
    def ensure_connection(self):
        """Ensure database connection is established."""
        if not self.postgres.connection:
            self.postgres.connect()
    
    def download_collection(self, download_artwork: bool = True, max_releases: Optional[int] = None, incremental_mode: bool = False):
        """Download complete collection data and artwork."""
        if incremental_mode:
            logger.info("Starting Discogs collection download (INCREMENTAL MODE - recent releases only)...")
        else:
            logger.info("Starting Discogs collection download...")
        
        # Connect to PostgreSQL
        self.postgres.connect()
        
        try:
            # Use configured username if available, otherwise get from API
            if hasattr(self, 'config') and self.config.username:
                username = self.config.username
                logger.info(f"Using configured username: {username}")
                # Still need to get user_id from API for internal tracking
                identity = self.api.get_user_identity()
                if not identity:
                    logger.error("Failed to get user identity for user_id")
                    return
                user_id = str(identity['id'])
            else:
                # Get user identity from API
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
                    
                    # In incremental mode, only process recently added releases (last month)
                    if incremental_mode:
                        from datetime import datetime, timedelta
                        
                        date_added_str = release.get('date_added')
                        if date_added_str:
                            try:
                                # Parse the date_added field (format: "2024-08-15T12:34:56-07:00")
                                date_added = datetime.fromisoformat(date_added_str.replace('Z', '+00:00'))
                                cutoff_date = datetime.now(date_added.tzinfo) - timedelta(days=30)
                                
                                if date_added < cutoff_date:
                                    logger.debug(f"Skipping old release from {date_added_str} (older than 30 days)")
                                    continue
                                else:
                                    logger.info(f"Processing recent release from {date_added_str}")
                            except Exception as e:
                                logger.warning(f"Could not parse date_added '{date_added_str}': {e}")
                                # If we can't parse the date, process it anyway to be safe
                    
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

    def download_wantlist(self, max_items: Optional[int] = None):
        """Download only the user's wantlist into Postgres."""
        logger.info("Starting Discogs wantlist download...")
        self.postgres.connect()
        try:
            # Use configured username if available, otherwise get from API
            if self.config.username:
                username = self.config.username
                logger.info(f"Using configured username: {username}")
                # Still need to get user_id from API for internal tracking
                identity = self.api.get_user_identity()
                if not identity:
                    logger.error("Failed to get user identity for user_id")
                    return
                user_id = str(identity['id'])
            else:
                # Get user identity from API
                identity = self.api.get_user_identity()
                if not identity:
                    logger.error("Failed to get user identity")
                    return
                username = identity['username']
                user_id = str(identity['id'])

            page = 1
            total = 0
            processed = 0
            while True:
                data = self.api.get_user_wantlist(username, page=page)
                if not data:
                    break
                if page == 1:
                    total = data.get('pagination', {}).get('items', 0)
                wants = data.get('wants', [])
                for want in wants:
                    if max_items and processed >= max_items:
                        logger.info(f"Reached wantlist limit: {max_items}")
                        return
                    bi = want.get('basic_information', {})
                    want_record = {
                        'want_id': f"want_{user_id}_{bi.get('id', uuid.uuid4().hex)}",
                        'user_id': user_id,
                        'username': username,
                        'discogs_release_id': bi.get('id'),
                        'title': bi.get('title'),
                        'artist': safe_extract_artists(bi.get('artists', [])),
                        'year': bi.get('year'),
                        'label': safe_extract_labels(bi.get('labels', [])),
                        'format': safe_extract_formats(bi.get('formats', [])),
                        'genres': safe_extract_list_field(bi.get('genres', [])),
                        'styles': safe_extract_list_field(bi.get('styles', [])),
                        'notes': want.get('notes'),
                        'rating': want.get('rating'),
                        'added': want.get('date_added'),
                        'basic_information': bi,
                        'raw_data': want
                    }
                    self._upsert_wantlist(want_record)
                    processed += 1
                if data.get('pagination', {}).get('page', 1) >= data.get('pagination', {}).get('pages', 1):
                    break
                page += 1
            logger.info(f"Wantlist download completed. Processed {processed} items (total {total}).")
        finally:
            self.postgres.disconnect()

    def _upsert_wantlist(self, want: Dict):
        query = """
        INSERT INTO wantlist (
            want_id, user_id, username, discogs_release_id, title, artist, year, label, format,
            genres, styles, notes, rating, added, basic_information, raw_data
        ) VALUES (
            %(want_id)s, %(user_id)s, %(username)s, %(discogs_release_id)s, %(title)s, %(artist)s, %(year)s, %(label)s, %(format)s,
            %(genres)s, %(styles)s, %(notes)s, %(rating)s, %(added)s, %(basic_information)s, %(raw_data)s
        )
        ON CONFLICT (want_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            artist = EXCLUDED.artist,
            year = EXCLUDED.year,
            label = EXCLUDED.label,
            format = EXCLUDED.format,
            genres = EXCLUDED.genres,
            styles = EXCLUDED.styles,
            notes = EXCLUDED.notes,
            rating = EXCLUDED.rating,
            added = EXCLUDED.added,
            basic_information = EXCLUDED.basic_information,
            raw_data = EXCLUDED.raw_data,
            last_updated = CURRENT_TIMESTAMP
        """

        processed = want.copy()
        for jf in ['genres', 'styles', 'basic_information', 'raw_data']:
            if jf in processed and processed[jf] is not None and not isinstance(processed[jf], str):
                processed[jf] = json.dumps(processed[jf])
        with self.postgres.connection.cursor() as cursor:
            cursor.execute(query, processed)
        self.postgres.connection.commit()

    @staticmethod
    def refresh_prices_via_script(batch_limit: Optional[int] = None, config: Optional['DiscogsConfig'] = None):
        """Invoke the repository's refresh_prices_postgres script programmatically."""
        try:
            # Load config if not provided
            if config is None:
                config = load_config()
            
            # Set environment variables from config for the script
            old_env = {}
            env_vars = {
                'DISCOGS_TOKEN': config.token,
                'PGHOST': config.postgres_host,
                'PGPORT': str(config.postgres_port),
                'PGDATABASE': config.postgres_database,
                'PGUSER': config.postgres_user,
                'PGPASSWORD': config.postgres_password
            }
            
            # Save old values and set new ones
            for key, value in env_vars.items():
                old_env[key] = os.environ.get(key)
                os.environ[key] = value
            
            try:
                # Fix path calculation - need parents[3] to reach discogs_project root
                repo_root = Path(__file__).resolve().parents[3]
                scripts_dir = repo_root / 'scripts'
                if str(repo_root) not in sys.path:
                    sys.path.insert(0, str(repo_root))
                if str(scripts_dir) not in sys.path:
                    sys.path.insert(0, str(scripts_dir))
                # Import and run
                try:
                    from scripts import refresh_prices_postgres as rpp  # type: ignore
                except Exception:
                    import importlib
                    rpp = importlib.import_module('scripts.refresh_prices_postgres')
                if batch_limit is None:
                    rpp.refresh_prices()
                else:
                    rpp.refresh_prices(batch_limit=batch_limit)
            finally:
                # Restore old environment variables
                for key, old_value in old_env.items():
                    if old_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old_value
                        
        except Exception as e:
            logger.error(f"Failed to refresh prices: {e}")
            raise

    def refresh_community_stats(self, batch_limit: int = 100):
        """Refresh community statistics for existing releases."""
        logger.info(f"Starting community statistics refresh with batch limit: {batch_limit}")
        
        # Get releases that need stats refresh (either never updated or older than 7 days)
        query = """
        SELECT release_id, discogs_id, title, artist, stats_last_updated
        FROM releases 
        WHERE discogs_id IS NOT NULL 
        AND (stats_last_updated IS NULL OR stats_last_updated < NOW() - INTERVAL '7 days')
        ORDER BY stats_last_updated ASC NULLS FIRST, created_date DESC
        LIMIT %s
        """
        
        releases = self.postgres.execute_query(query, (batch_limit,))
        if not releases:
            logger.info("No releases found that need community statistics refresh")
            return
        
        logger.info(f"Found {len(releases)} releases that need community statistics refresh")
        
        updated_count = 0
        for release in releases:
            try:
                discogs_id = release.get('discogs_id')
                if not discogs_id:
                    continue
                
                # Fetch release statistics
                stats = self.api.get_release_statistics(discogs_id)
                if stats:
                    # Update the release with community statistics
                    update_query = """
                    UPDATE releases 
                    SET community_have_count = %s,
                        community_want_count = %s,
                        community_rating_count = %s,
                        community_average_rating = %s,
                        stats_last_updated = CURRENT_TIMESTAMP,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE release_id = %s
                    """
                    
                    with self.postgres.connection.cursor() as cursor:
                        cursor.execute(update_query, (
                            stats['have_count'],
                            stats['want_count'],
                            stats['rating_count'],
                            stats['average_rating'],
                            release['release_id']
                        ))
                    self.postgres.connection.commit()
                    
                    updated_count += 1
                    logger.info(f"Updated stats for '{release.get('title', 'Unknown')}' by {release.get('artist', 'Unknown')}: "
                              f"Have: {stats['have_count']}, Want: {stats['want_count']}, "
                              f"Rating: {stats['average_rating']} ({stats['rating_count']} votes)")
                    
                    # Rate limiting to be respectful to Discogs API
                    time.sleep(1.0)
                    
            except Exception as e:
                logger.error(f"Error refreshing stats for release {release.get('release_id')}: {e}")
                continue
        
        logger.info(f"Community statistics refresh completed. Updated {updated_count} releases.")

    def refresh_community_stats_for_release(self, discogs_release_id: int) -> bool:
        """Refresh community stats for a single release id."""
        try:
            stats = self.api.get_release_statistics(discogs_release_id)
            if not stats:
                return False
            update_query = """
            UPDATE releases 
            SET community_have_count = %s,
                community_want_count = %s,
                community_rating_count = %s,
                community_average_rating = %s,
                stats_last_updated = CURRENT_TIMESTAMP,
                last_updated = CURRENT_TIMESTAMP
            WHERE discogs_id = %s
            """
            with self.postgres.connection.cursor() as cursor:
                cursor.execute(update_query, (
                    stats['have_count'],
                    stats['want_count'],
                    stats['rating_count'],
                    stats['average_rating'],
                    discogs_release_id
                ))
            self.postgres.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh community stats for {discogs_release_id}: {e}")
            return False

    def refresh_marketplace_for_release(self, discogs_release_id: int) -> bool:
        """Refresh current marketplace listing info for a single release and upsert tables."""
        try:
            mp = self.api.get_marketplace_stats(discogs_release_id)
            if not mp:
                return False
            lowest = mp.get('lowest_price') or {}
            low_value = lowest.get('value')
            currency = lowest.get('currency')
            num_for_sale = mp.get('num_for_sale')
            blocked = mp.get('blocked_from_sale', False)

            # Upsert release_prices
            upsert_prices = """
            INSERT INTO release_prices (discogs_release_id, lowest_price, currency, num_for_sale, availability, last_seen, source)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'discogs_public_api')
            ON CONFLICT (discogs_release_id) DO UPDATE SET
                lowest_price = EXCLUDED.lowest_price,
                currency = EXCLUDED.currency,
                num_for_sale = EXCLUDED.num_for_sale,
                availability = EXCLUDED.availability,
                last_seen = EXCLUDED.last_seen,
                source = EXCLUDED.source
            """
            with self.postgres.connection.cursor() as cur:
                cur.execute(upsert_prices, (
                    discogs_release_id, low_value, currency, num_for_sale, not blocked
                ))
            self.postgres.connection.commit()

            # Upsert SCD1 dim from current snapshot (historical sold not available)
            upsert_dim = """
            INSERT INTO marketplace_stats_dim (discogs_release_id, last_sold_date, low_sold_price, high_sold_price, currency, as_of, notes)
            VALUES (%s, NULL, %s, NULL, %s, CURRENT_TIMESTAMP, 'Populated from current marketplace listings; historical sold data not available')
            ON CONFLICT (discogs_release_id) DO UPDATE SET
                last_sold_date = EXCLUDED.last_sold_date,
                low_sold_price = EXCLUDED.low_sold_price,
                high_sold_price = EXCLUDED.high_sold_price,
                currency = EXCLUDED.currency,
                as_of = EXCLUDED.as_of,
                notes = EXCLUDED.notes
            """
            with self.postgres.connection.cursor() as cur:
                cur.execute(upsert_dim, (discogs_release_id, low_value, currency))
            self.postgres.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh marketplace for {discogs_release_id}: {e}")
            return False

    def ingest_marketplace_sales_csv(self, csv_path: str) -> int:
        """Ingest a CSV of historical sold stats into marketplace_stats_dim (SCD1 overwrite).

        Expected columns: discogs_release_id,last_sold_date,low_sold_price,high_sold_price,currency
        """
        import csv
        count = 0
        try:
            with open(csv_path, newline='') as f:
                reader = csv.DictReader(f)
                with self.postgres.connection.cursor() as cur:
                    for row in reader:
                        try:
                            discogs_id = int(row.get('discogs_release_id'))
                            last_sold_date = row.get('last_sold_date') or None
                            low_price = row.get('low_sold_price')
                            high_price = row.get('high_sold_price')
                            currency = row.get('currency')
                            cur.execute(
                                """
                                INSERT INTO marketplace_stats_dim (discogs_release_id, last_sold_date, low_sold_price, high_sold_price, currency, as_of, notes)
                                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'Ingested via CSV')
                                ON CONFLICT (discogs_release_id) DO UPDATE SET
                                    last_sold_date = EXCLUDED.last_sold_date,
                                    low_sold_price = EXCLUDED.low_sold_price,
                                    high_sold_price = EXCLUDED.high_sold_price,
                                    currency = EXCLUDED.currency,
                                    as_of = EXCLUDED.as_of,
                                    notes = EXCLUDED.notes
                                """,
                                (discogs_id, last_sold_date, low_price, high_price, currency)
                            )
                            count += 1
                        except Exception as ie:
                            logger.warning(f"Skipping row due to error: {ie}")
                self.postgres.connection.commit()
            logger.info(f"Ingested {count} marketplace sales rows from {csv_path}")
            return count
        except Exception as e:
            logger.error(f"Failed to ingest CSV {csv_path}: {e}")
            return 0

    def fix_missing_country(self, batch_limit: Optional[int] = 500):
        """Fix missing or invalid country fields for releases by fetching details from Discogs.

        Only updates `releases.country` (and year if absent) and does nothing else.
        """
        logger.info("Fixing missing country information for releases...")
        self.postgres.connect()
        try:
            with self.postgres.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT release_id, discogs_id, country, year
                    FROM releases
                    WHERE discogs_id IS NOT NULL
                      AND (country IS NULL OR country = '' OR country = '0')
                    ORDER BY last_updated NULLS LAST
                    LIMIT %s
                    """,
                    (batch_limit,)
                )
                rows = cursor.fetchall()
            if not rows:
                logger.info("No releases with missing country found.")
                return
            updated = 0
            for row in rows:
                rid = row['release_id']
                did = row['discogs_id']
                try:
                    details = self.api.get_release_details(int(did))
                except Exception as e:
                    logger.warning(f"Failed to fetch details for discogs_id={did}: {e}")
                    continue
                if not isinstance(details, dict):
                    continue
                new_country = details.get('country')
                new_year = details.get('year')
                if new_country:
                    with self.postgres.connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE releases
                            SET country = %s,
                                year = COALESCE(year, %s),
                                last_updated = CURRENT_TIMESTAMP
                            WHERE release_id = %s
                            """,
                            (new_country, new_year, rid)
                        )
                    updated += 1
                    if updated % 50 == 0:
                        self.postgres.connection.commit()
            self.postgres.connection.commit()
            logger.info(f"Updated country for {updated} releases.")
        finally:
            self.postgres.disconnect()
    
    def _process_release(self, collection_id: str, release_data: Dict, download_artwork: bool = True):
        """Process a single release from the collection."""
        try:
            basic_info = release_data.get('basic_information', {})
            release_id = f"release_{release_data.get('id', uuid.uuid4().hex)}"
            
            # Safely extract data using robust functions
            try:
                artist_names = safe_extract_artists(basic_info.get('artists', []))
                label_names = safe_extract_labels(basic_info.get('labels', []))
                catalog_numbers = safe_extract_catalog_numbers(basic_info.get('labels', []))
                format_names = safe_extract_formats(basic_info.get('formats', []))
                genres_list = safe_extract_list_field(basic_info.get('genres', []))
                styles_list = safe_extract_list_field(basic_info.get('styles', []))
                notes_value = safe_extract_notes(release_data.get('notes'))
                # Extract producers from extraartists if available
                producers_list = []
                try:
                    for ea in basic_info.get('extraartists', []) or []:
                        if isinstance(ea, dict) and 'role' in ea and 'name' in ea:
                            role = str(ea.get('role', '')).lower()
                            if 'producer' in role:
                                name = ea.get('name')
                                if name and name not in producers_list:
                                    producers_list.append(name)
                except Exception:
                    producers_list = []
            except Exception as e:
                logger.warning(f"Error during safe extraction for release {release_id}: {e}")
                # Fallback to empty values if extraction fails
                artist_names = ''
                label_names = ''
                catalog_numbers = ''
                format_names = ''
                genres_list = []
                styles_list = []
                notes_value = None
                producers_list = []

            # Fetch detailed release if we need missing fields like country/year or community stats
            detailed_release = None
            country_value = basic_info.get('country')
            year_value = basic_info.get('year')
            community_stats = {}
            
            # Always fetch detailed release to get community statistics
            try:
                detailed_release = self.api.get_release_details(basic_info.get('id'))
                if detailed_release:
                    if not country_value:
                        country_value = detailed_release.get('country', country_value)
                    if not year_value:
                        year_value = detailed_release.get('year', year_value)
                    
                    # Extract community statistics
                    community = detailed_release.get('community', {})
                    rating_data = community.get('rating', {})
                    community_stats = {
                        'community_have_count': community.get('have', 0),
                        'community_want_count': community.get('want', 0),
                        'community_rating_count': rating_data.get('count', 0),
                        'community_average_rating': rating_data.get('average', 0.0),
                        'stats_last_updated': datetime.now()
                    }

                # Optional current marketplace stats (for sale count, lowest listing price)
                try:
                    mp = self.api.get_marketplace_stats(basic_info.get('id'))
                    if mp:
                        # store minimal snapshot alongside release row
                        release_marketplace_stats = {
                            'num_for_sale': mp.get('num_for_sale'),
                            'lowest_price': mp.get('lowest_price'),
                            'blocked_from_sale': mp.get('blocked_from_sale')
                        }
                    else:
                        release_marketplace_stats = {}
                except Exception:
                    release_marketplace_stats = {}
            except Exception as e:
                logger.debug(f"Could not fetch detailed release info for {basic_info.get('id')}: {e}")
                community_stats = {
                    'community_have_count': 0,
                    'community_want_count': 0,
                    'community_rating_count': 0,
                    'community_average_rating': 0.0,
                    'stats_last_updated': None
                }
                release_marketplace_stats = {}
            
            # Extract basic information
            # Build instance_ids list to aggregate duplicates
            existing = self.postgres.execute_query(
                "SELECT release_id, instance_ids, copies_count FROM releases WHERE discogs_id = %s",
                (basic_info.get('id'),)
            )

            aggregated_instance_ids = []
            aggregated_copies = 1
            if existing:
                row = existing[0]
                try:
                    if row.get('instance_ids'):
                        aggregated_instance_ids = json.loads(row['instance_ids']) if isinstance(row['instance_ids'], str) else row['instance_ids']
                        if not isinstance(aggregated_instance_ids, list):
                            aggregated_instance_ids = []
                except Exception:
                    aggregated_instance_ids = []
                prev_copies = row.get('copies_count') or 1
                aggregated_copies = max(int(prev_copies), 1)

            current_instance_id = release_data.get('instance_id')
            if current_instance_id and current_instance_id not in aggregated_instance_ids:
                aggregated_instance_ids.append(current_instance_id)
                aggregated_copies = len(aggregated_instance_ids)

            release_info = {
                'release_id': release_id,
                'collection_id': collection_id,
                'basic_information': basic_info,
                'discogs_id': basic_info.get('id'),
                'title': basic_info.get('title'),
                'artist': artist_names,
                'year': year_value,
                'label': label_names,
                'catno': catalog_numbers,
                'format': format_names,
                'genres': genres_list,
                'styles': styles_list,
                'producers': producers_list,
                'copies_count': aggregated_copies,
                'instance_ids': aggregated_instance_ids,
                'country': country_value,
                'date_added': release_data.get('date_added'),
                'instance_id': release_data.get('instance_id'),
                'folder_id': release_data.get('folder_id'),
                'rating': release_data.get('rating'),
                'notes': notes_value,
                'condition': release_data.get('condition'),
                'sleeve_condition': release_data.get('sleeve_condition'),
                'marketplace_stats': release_marketplace_stats,
                'artwork_urls': [],
                'local_artwork_paths': [],
                'raw_data': release_data,
                **community_stats  # Add community statistics
            }
            
            # Download artwork if requested and collect artwork data
            artwork_records = []
            artwork_urls = []
            if download_artwork and basic_info.get('thumb'):
                # Skip downloading if artwork already exists for this release
                existing_art = self.postgres.execute_query(
                    "SELECT COUNT(*) AS cnt FROM artwork WHERE release_id = %s",
                    (release_id,)
                )
                if existing_art and existing_art[0].get('cnt', 0) and int(existing_art[0]['cnt']) > 0:
                    logger.debug(f"Artwork already present in DB for {release_id}; skipping download.")
                else:
                    artwork_urls = [basic_info['thumb']]
                    
                    # Get additional images from detailed release info
                    if detailed_release is None:
                        detailed_release = self.api.get_release_details(basic_info.get('id'))
                    
                    # Collect image data (not just URLs)
                    image_data_list = []
                    if detailed_release and detailed_release.get('images'):
                        image_data_list = detailed_release['images']
                        artwork_urls.extend([img['uri'] for img in detailed_release['images']])
                    else:
                        # Fallback: create image data from thumb URL
                        image_data_list = [{'uri': basic_info['thumb'], 'type': 'primary'}]
                    
                    release_info['artwork_urls'] = artwork_urls
                    
                    # Download each image but don't save to DB yet
                    local_paths = []
                    for i, image_data in enumerate(image_data_list):
                        image_type = image_data.get('type', f"image_{i}")
                        if i == 0:
                            image_type = "primary"
                        
                        # Use the full image data for proper URL extraction
                        image_url = image_data.get('uri', '')
                        result = self.artwork_downloader.download_image(
                            image_url, release_id, image_type, 
                            download_thumbnail=True, image_data=image_data
                        )
                        
                        if result:
                            local_file_path, metadata = result
                            local_paths.append(local_file_path)
                            
                            # Prepare artwork record for later insertion
                            artwork_data = {
                                'artwork_id': f"artwork_{release_id}_{i}",
                                'release_id': release_id,
                                'image_type': image_type,
                                'original_url': image_url,
                                **metadata
                            }
                            artwork_records.append(artwork_data)
                    
                    release_info['local_artwork_paths'] = local_paths
            
            # IMPORTANT: Save release to database FIRST (to satisfy foreign key constraint)
            self.postgres.upsert_release(release_info)
            
            # Process track information for detailed track listings
            self._process_tracks(
                release_id,
                detailed_release if 'detailed_release' in locals() else None,
                basic_info.get('id')
            )

            # Process artist discography for completeness analysis
            # Handle Various Artists compilations by avoiding artist API calls that can 404
            artists_list = basic_info.get('artists', []) or []
            is_various = False
            try:
                for artist_entry in artists_list:
                    if isinstance(artist_entry, dict):
                        name_value = artist_entry.get('name', '')
                    else:
                        name_value = str(artist_entry)
                    if name_value.strip().lower() in {"various", "various artists", "va"}:
                        is_various = True
                        break
            except Exception:
                # Be resilient if structure is unexpected
                is_various = False

            if is_various:
                # Create a pseudo-artist based on album title to index compilations by title
                try:
                    compilation_title = basic_info.get('title', f"compilation_{release_id}")
                    pseudo_artist_id = f"comp_{release_id}"
                    pseudo_artist_record = {
                        'artist_id': pseudo_artist_id,
                        'artist_name': f"Compilation: {compilation_title}",
                        'discogs_artist_id': None,
                        'raw_data': {
                            'type': 'compilation',
                            'source': 'various_artists_fallback',
                            'release_id': release_id,
                            'title': compilation_title
                        }
                    }
                    self._upsert_artist(pseudo_artist_record)

                    # Link this release into artist_discography as an owned item
                    discography_id = f"disco_{pseudo_artist_id}_{release_id}"
                    discography_data = {
                        'discography_id': discography_id,
                        'artist_id': pseudo_artist_id,
                        'discogs_artist_id': -1,
                        'artist_name': pseudo_artist_record['artist_name'],
                        'release_id': discography_id,
                        'discogs_release_id': basic_info.get('id'),
                        'title': compilation_title,
                        'year': basic_info.get('year'),
                        'role': 'Compilation',
                        'label': ", ".join([lbl.get('name', '') for lbl in basic_info.get('labels', [])]) if isinstance(basic_info.get('labels'), list) else basic_info.get('label', ''),
                        'format': ", ".join([fmt.get('name', '') for fmt in basic_info.get('formats', [])]) if isinstance(basic_info.get('formats'), list) else basic_info.get('format', ''),
                        'country': basic_info.get('country', ''),
                        'in_collection': True,
                        'collection_release_id': release_id,
                        'raw_data': basic_info
                    }
                    self.postgres.upsert_artist_discography(discography_data)
                    logger.info(f"Handled Various Artists compilation via title fallback for release {release_id}")
                except Exception as va_err:
                    logger.warning(f"Failed to apply Various Artists fallback for release {release_id}: {va_err}")
            else:
                # Normal per-artist processing
                self._process_artist_discography(artists_list, release_id)
            
            # Now save artwork records (release_id now exists in database)
            for artwork_data in artwork_records:
                try:
                    self.postgres.upsert_artwork(artwork_data)
                    logger.debug(f"Successfully saved artwork: {artwork_data['artwork_id']}")
                except Exception as artwork_error:
                    logger.warning(f"Failed to save artwork {artwork_data['artwork_id']}: {artwork_error}")
                    # Continue with other artwork - don't fail the entire release
            
        except Exception as e:
            # Log detailed error information
            release_id = release_data.get('id', 'unknown')
            logger.error(f"Error processing release {release_id}: {e}")
            
            # Log problematic data structure for debugging
            if 'list' in str(e) and 'get' in str(e):
                try:
                    basic_info = release_data.get('basic_information', {})
                    logger.error(f"Problematic data structures for release {release_id}:")
                    
                    artists = basic_info.get('artists', [])
                    if artists:
                        logger.error(f"  Artists type: {type(artists)}, sample: {artists[:2] if isinstance(artists, list) else artists}")
                    
                    labels = basic_info.get('labels', [])
                    if labels:
                        logger.error(f"  Labels type: {type(labels)}, sample: {labels[:2] if isinstance(labels, list) else labels}")
                    
                    formats = basic_info.get('formats', [])
                    if formats:
                        logger.error(f"  Formats type: {type(formats)}, sample: {formats[:2] if isinstance(formats, list) else formats}")
                    
                    notes = release_data.get('notes')
                    if notes:
                        logger.error(f"  Notes type: {type(notes)}, value: {notes}")
                        
                except Exception as debug_error:
                    logger.error(f"Error during debugging info collection: {debug_error}")
            
            # Continue processing other releases
            pass
    
    def _process_tracks(self, release_id: str, detailed_release: Optional[Dict], discogs_release_id: Optional[int]):
        """Process and store track information for a release."""
        try:
            # Get detailed release information if not already available
            if not detailed_release and discogs_release_id:
                detailed_release = self.api.get_release_details(discogs_release_id)
            
            if not detailed_release or 'tracklist' not in detailed_release:
                logger.debug(f"No tracklist available for release {release_id}")
                return
            
            tracklist = detailed_release.get('tracklist', [])
            for i, track in enumerate(tracklist):
                if not isinstance(track, dict):
                    continue
                
                track_id = f"track_{release_id}_{i}"
                
                # Extract track artists (important for Various Artists albums)
                track_artists = []
                if 'artists' in track:
                    for artist in track.get('artists', []):
                        if isinstance(artist, dict) and 'name' in artist:
                            track_artists.append(artist['name'])
                        elif isinstance(artist, str):
                            track_artists.append(artist)
                
                # Extract extra artists (featuring, remix, etc.)
                extra_artists = []
                if 'extraartists' in track:
                    for extra_artist in track.get('extraartists', []):
                        if isinstance(extra_artist, dict):
                            extra_artists.append({
                                'name': extra_artist.get('name', ''),
                                'role': extra_artist.get('role', ''),
                                'tracks': extra_artist.get('tracks', '')
                            })
                
                track_data = {
                    'track_id': track_id,
                    'release_id': release_id,
                    'track_number': track.get('position', ''), # Maps Discogs 'position' to our 'track_number'
                    'title': track.get('title', ''),
                    'duration': track.get('duration', ''),
                    'artists': track_artists,
                    'extraartists': extra_artists,
                    'raw_track_data': track
                }
                
                self.postgres.upsert_track(track_data)
                
            logger.debug(f"Processed {len(tracklist)} tracks for release {release_id}")
            
        except Exception as e:
            logger.error(f"Error processing tracks for release {release_id}: {e}")
    
    def _process_artist_discography(self, artists: List[Dict], collection_release_id: str):
        """Process artist discography to identify missing releases."""
        try:
            for artist_data in artists:
                if not isinstance(artist_data, dict) or 'id' not in artist_data:
                    continue
                
                discogs_artist_id = artist_data.get('id')
                artist_name = artist_data.get('name', '')
                
                # Create or get artist record
                artist_id = f"artist_{discogs_artist_id}"
                artist_record = {
                    'artist_id': artist_id,
                    'artist_name': artist_name,
                    'discogs_artist_id': discogs_artist_id,
                    'raw_data': artist_data
                }
                
                # Upsert artist
                self._upsert_artist(artist_record)
                
                # Get artist's full discography from Discogs (limit to avoid too many API calls)
                self._fetch_artist_discography(artist_id, discogs_artist_id, artist_name, collection_release_id)
                
        except Exception as e:
            logger.error(f"Error processing artist discography: {e}")
    
    def _upsert_artist(self, artist_data: Dict):
        """Insert or update artist information with full details."""
        try:
            query = """
            INSERT INTO artists (
                artist_id, artist_name, real_name, profile, discogs_artist_id, 
                images, urls, members, groups, aliases, raw_data
            )
            VALUES (
                %(artist_id)s, %(artist_name)s, %(real_name)s, %(profile)s, %(discogs_artist_id)s,
                %(images)s, %(urls)s, %(members)s, %(groups)s, %(aliases)s, %(raw_data)s
            )
            ON CONFLICT (artist_id) DO UPDATE SET
                artist_name = EXCLUDED.artist_name,
                real_name = EXCLUDED.real_name,
                profile = EXCLUDED.profile,
                images = EXCLUDED.images,
                urls = EXCLUDED.urls,
                members = EXCLUDED.members,
                groups = EXCLUDED.groups,
                aliases = EXCLUDED.aliases,
                raw_data = EXCLUDED.raw_data,
                last_updated = CURRENT_TIMESTAMP
            """
            
            # Extract and prepare data
            processed_data = {
                'artist_id': artist_data.get('artist_id', f"artist_{artist_data.get('id')}"),
                'artist_name': artist_data.get('name'),
                'real_name': artist_data.get('real_name'),
                'profile': artist_data.get('profile'),
                'discogs_artist_id': artist_data.get('id'),
                'images': json.dumps(artist_data.get('images', [])),
                'urls': json.dumps(artist_data.get('urls', [])),
                'members': json.dumps(artist_data.get('members', [])),
                'groups': json.dumps(artist_data.get('groups', [])),
                'aliases': json.dumps(artist_data.get('aliases', [])),
                'raw_data': json.dumps(artist_data)
            }
            
            if self.postgres.connection:
                with self.postgres.connection.cursor() as cursor:
                    cursor.execute(query, processed_data)
                self.postgres.connection.commit()
            else:
                logger.error("No database connection available")
                
        except Exception as e:
            logger.error(f"Error upserting artist {artist_data.get('name', 'unknown')}: {e}")
    
    def refresh_artist_details(self, artist_id: int = None, artist_name: str = None):
        """Refresh detailed artist information from Discogs API."""
        self.ensure_connection()
        try:
            if artist_id:
                # Direct artist ID provided
                artist_data = self.api.get_artist_details(artist_id)
                if artist_data:
                    logger.info(f"Refreshing artist data for ID {artist_id}: {artist_data.get('name')}")
                    self._upsert_artist(artist_data)
                    return True
                else:
                    logger.error(f"Could not fetch artist data for ID {artist_id}")
                    return False
            
            elif artist_name:
                # Find artist by name in database first
                query = """
                SELECT discogs_artist_id FROM artists 
                WHERE LOWER(artist_name) LIKE LOWER(%s)
                LIMIT 1
                """
                if not self.postgres.connection:
                    logger.error("No database connection available")
                    return False
                    
                with self.postgres.connection.cursor() as cursor:
                    cursor.execute(query, (f'%{artist_name}%',))
                    result = cursor.fetchone()
                
                if result and result[0]:
                    discogs_id = result[0]
                    return self.refresh_artist_details(artist_id=discogs_id)
                else:
                    logger.error(f"Could not find artist '{artist_name}' in database")
                    return False
            else:
                logger.error("Either artist_id or artist_name must be provided")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing artist details: {e}")
            return False
    
    def refresh_all_artists(self, batch_size: int = None):
        """Refresh all artists with missing detailed information."""
        self.ensure_connection()
        try:
            # Find artists with missing detailed info
            if batch_size:
                query = """
                SELECT discogs_artist_id, artist_name 
                FROM artists 
                WHERE discogs_artist_id IS NOT NULL 
                AND (real_name IS NULL OR aliases IS NULL OR groups IS NULL)
                ORDER BY last_updated ASC
                LIMIT %s
                """
            else:
                query = """
                SELECT discogs_artist_id, artist_name 
                FROM artists 
                WHERE discogs_artist_id IS NOT NULL 
                AND (real_name IS NULL OR aliases IS NULL OR groups IS NULL)
                ORDER BY last_updated ASC
                """
            
            if not self.postgres.connection:
                logger.error("No database connection available")
                return False
                
            with self.postgres.connection.cursor() as cursor:
                if batch_size:
                    cursor.execute(query, (batch_size,))
                else:
                    cursor.execute(query)
                results = cursor.fetchall()
            
            if not results:
                logger.info("No artists found that need refreshing")
                return True
            
            logger.info(f"Refreshing {len(results)} artists with missing information")
            
            for artist in results:
                discogs_id = artist[0]
                artist_name = artist[1]
                
                logger.info(f"Refreshing {artist_name} (ID: {discogs_id})")
                self.refresh_artist_details(artist_id=discogs_id)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing all artists: {e}")
            return False

    def _fetch_artist_discography(self, artist_id: str, discogs_artist_id: int, artist_name: str, collection_release_id: str):
        """Fetch limited artist discography from Discogs (first 50 releases to avoid rate limits)."""
        try:
            # Get first page of artist releases (limit to avoid too many API calls)
            artist_releases = self.api._make_request(f"/artists/{discogs_artist_id}/releases", {'page': 1, 'per_page': 50})
            
            if not artist_releases or 'releases' not in artist_releases:
                logger.info(f"No releases found for artist '{artist_name}' (id={discogs_artist_id}); skipping.")
                return
            
            releases = artist_releases.get('releases', [])
            for release in releases[:50]:  # Limit to first 50 releases
                if not isinstance(release, dict):
                    continue
                
                discography_id = f"disco_{artist_id}_{release.get('id', uuid.uuid4().hex)}"
                
                # Check if this release is in our collection
                in_collection = False
                collection_release_match = None
                
                existing_release = self.postgres.execute_query(
                    "SELECT release_id FROM releases WHERE discogs_id = %s",
                    (release.get('id'),)
                )
                
                if existing_release:
                    in_collection = True
                    collection_release_match = existing_release[0]['release_id']
                
                discography_data = {
                    'discography_id': discography_id,
                    'artist_id': artist_id,
                    'discogs_artist_id': discogs_artist_id,
                    'artist_name': artist_name,
                    'release_id': discography_id,
                    'discogs_release_id': release.get('id'),
                    'title': release.get('title', ''),
                    'year': release.get('year'),
                    'role': release.get('role', 'Main'),
                    'label': release.get('label', ''),
                    'format': release.get('format', ''),
                    'country': release.get('country', ''),
                    'in_collection': in_collection,
                    'collection_release_id': collection_release_match,
                    'raw_data': release
                }
                
                self.postgres.upsert_artist_discography(discography_data)
                
            logger.debug(f"Processed limited discography for artist {artist_name}")
            
        except Exception as e:
            logger.error(f"Error fetching discography for artist {artist_name}: {e}")

class PhotosOnlyDownloader:
    """Downloads only missing photos for existing releases in the database."""
    
    def __init__(self, config: DiscogsConfig):
        self.config = config
        self.postgres = PostgreSQLManager(config)
        self.artwork_downloader = ArtworkDownloader(config.local_artwork_path)
        self.api = DiscogsAPI(config.token, config.user_agent)
        
    def get_releases_without_artwork(self) -> List[Tuple[str, int, List[str]]]:
        """Get releases that don't have downloaded artwork."""
        query = """
        SELECT DISTINCT r.release_id, r.discogs_id, r.artwork_urls
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
        for release_id, discogs_id, artwork_urls_json in results:
            if artwork_urls_json:
                try:
                    import json
                    artwork_urls = json.loads(artwork_urls_json) if isinstance(artwork_urls_json, str) else artwork_urls_json
                    if artwork_urls:
                        releases_to_download.append((release_id, discogs_id, artwork_urls))
                except Exception as e:
                    logger.warning(f"Could not parse artwork URLs for release {release_id}: {e}")
        
        return releases_to_download
    
    def download_missing_photos(self, force_redownload: bool = False, max_releases: Optional[int] = None):
        """Download missing photos for releases with full-size and thumbnail support."""
        # Connect to database
        self.postgres.connect()
        
        try:
            releases_to_download = self.get_releases_without_artwork()
            
            if max_releases:
                releases_to_download = releases_to_download[:max_releases]
            
            logger.info(f"Found {len(releases_to_download)} releases without artwork")
            
            for i, (release_id, discogs_id, artwork_urls) in enumerate(releases_to_download, 1):
                logger.info(f"Processing release {i}/{len(releases_to_download)}: {release_id}")
                
                try:
                    # Get detailed release info to access full image data
                    detailed_release = None
                    if discogs_id:
                        try:
                            detailed_release = self.api.get_release_details(int(discogs_id))
                            logger.debug(f"Retrieved detailed release info for {discogs_id}")
                        except Exception as api_error:
                            logger.warning(f"Could not get detailed release info for {discogs_id}: {api_error}")
                    
                    # Get image data list
                    image_data_list = []
                    if detailed_release and detailed_release.get('images'):
                        image_data_list = detailed_release['images']
                        logger.info(f"Found {len(image_data_list)} images in detailed release data")
                    else:
                        # Fallback: create basic image data from URLs
                        for j, url in enumerate(artwork_urls):
                            if url:
                                image_data_list.append({
                                    'uri': url,
                                    'type': 'primary' if j == 0 else 'secondary'
                                })
                        logger.info(f"Using fallback image data for {len(image_data_list)} images")
                    
                    # Download each image with full-size and thumbnail support
                    for j, image_data in enumerate(image_data_list):
                        image_url = image_data.get('uri', '')
                        if not image_url:
                            continue
                            
                        image_type = image_data.get('type', f"image_{j}")
                        if j == 0:
                            image_type = "primary"
                        
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
                        
                        # Download both full-size and thumbnail using enhanced method
                        logger.info(f"Downloading {image_type} image (full-size + thumbnail)")
                        result = self.artwork_downloader.download_image(
                            image_url=image_url,
                            release_id=release_id,
                            image_type=image_type,
                            download_thumbnail=True,
                            image_data=image_data
                        )
                        
                        if result:
                            local_file_path, metadata = result
                            
                            # Create artwork record
                            artwork_data = {
                                'artwork_id': f"artwork_{release_id}_{j}",
                                'release_id': release_id,
                                'image_type': image_type,
                                'original_url': image_url,
                                **metadata
                            }
                            
                            try:
                                self.postgres.upsert_artwork(artwork_data)
                                logger.info(f"Saved artwork to DB: {artwork_data['artwork_id']} (full-size: {metadata.get('file_size', 0)} bytes, thumbnail: {metadata.get('thumbnail_file_path', 'N/A')})")
                            except Exception as artwork_error:
                                logger.error(f"Failed to save artwork {artwork_data['artwork_id']}: {artwork_error}")
                                # Continue with next image - don't fail entire release
                        else:
                            logger.warning(f"Failed to download {image_type} image for {release_id}")
                        
                        # Rate limiting
                        time.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error processing release {release_id}: {e}")
                    
        finally:
            if self.postgres.connection:
                self.postgres.connection.close()

def load_config() -> DiscogsConfig:
    """Load configuration from local secrets.toml, environment variables, or JSON config file.

    Priority: .streamlit/secrets.toml → env vars → discogs_config.json
    """
    # 1) Try local secrets.toml
    def find_secrets_file() -> Optional[Path]:
        candidates = [
            Path('.streamlit/secrets.toml'),
            Path(__file__).resolve().parents[2] / '.streamlit' / 'secrets.toml',
            Path('secrets.toml')
        ]
        for p in candidates:
            try:
                if p.exists():
                    return p
            except Exception:
                continue
        return None

    secrets_path = find_secrets_file()
    if secrets_path and tomli is not None:
        try:
            logger.info(f"Found secrets.toml at: {secrets_path}")
            with open(secrets_path, 'rb') as f:
                secrets = tomli.load(f)
            logger.info(f"Loaded secrets sections: {list(secrets.keys())}")
            discogs_sec = secrets.get('discogs', secrets)
            pg_sec = secrets.get('postgres', secrets)
            token = discogs_sec.get('token') or os.getenv('DISCOGS_TOKEN')
            logger.info(f"Token from TOML: {'***FOUND***' if discogs_sec.get('token') else 'NOT FOUND'}")
            user_agent = discogs_sec.get('user_agent') or os.getenv('DISCOGS_USER_AGENT', 'DiscogsCollectionDownloader/1.0')
            username = discogs_sec.get('username') or os.getenv('DISCOGS_USERNAME')  # Optional username override
            postgres_host = pg_sec.get('host') or os.getenv('POSTGRES_HOST', 'localhost')
            postgres_port = int(pg_sec.get('port') or os.getenv('POSTGRES_PORT', '5432'))
            postgres_user = pg_sec.get('user') or os.getenv('POSTGRES_USER', 'discogs_user')
            postgres_password = pg_sec.get('password') or os.getenv('POSTGRES_PASSWORD')
            postgres_database = pg_sec.get('database') or os.getenv('POSTGRES_DATABASE', 'discogs_collection')
            postgres_schema = pg_sec.get('schema') or os.getenv('POSTGRES_SCHEMA', 'collection_data')
            if token and postgres_user and postgres_password:
                logger.info("Successfully loaded config from secrets.toml")
                return DiscogsConfig(
                    token=token,
                    user_agent=user_agent,
                    username=username,
                    postgres_host=postgres_host,
                    postgres_port=postgres_port,
                    postgres_user=postgres_user,
                    postgres_password=postgres_password,
                    postgres_database=postgres_database,
                    postgres_schema=postgres_schema
                )
            else:
                logger.warning(f"Missing required config: token={bool(token)}, user={bool(postgres_user)}, password={bool(postgres_password)}")
        except Exception as e:
            logger.warning(f"Failed to read secrets.toml at {secrets_path}: {e}")
    else:
        if not secrets_path:
            logger.info("No secrets.toml file found")
        if tomli is None:
            logger.warning("tomli/tomllib not available - cannot read TOML files")

    # 2) Environment variables (support both POSTGRES_* and PG* aliases)
    token = os.getenv('DISCOGS_TOKEN')
    user_agent = os.getenv('DISCOGS_USER_AGENT', 'DiscogsCollectionDownloader/1.0')
    username = os.getenv('DISCOGS_USERNAME')  # Optional username override
    postgres_host = os.getenv('POSTGRES_HOST', os.getenv('PGHOST', 'localhost'))
    postgres_port = int(os.getenv('POSTGRES_PORT', os.getenv('PGPORT', '5432')))
    postgres_user = os.getenv('POSTGRES_USER', os.getenv('PGUSER', 'discogs_user'))
    postgres_password = os.getenv('POSTGRES_PASSWORD', os.getenv('PGPASSWORD'))
    postgres_database = os.getenv('POSTGRES_DATABASE', os.getenv('PGDATABASE', 'discogs_collection'))
    postgres_schema = os.getenv('POSTGRES_SCHEMA', os.getenv('PGSCHEMA', 'collection_data'))
    if token and postgres_user and postgres_password:
        return DiscogsConfig(
            token=token,
            user_agent=user_agent,
            username=username,
            postgres_host=postgres_host,
            postgres_port=postgres_port,
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            postgres_database=postgres_database,
            postgres_schema=postgres_schema
        )

    # 3) Fallback to JSON config
    config_file = Path('discogs_config.json')
    if config_file.exists():
        with open(config_file) as f:
            config_data = json.load(f)
        return DiscogsConfig(**config_data)

    print("Configuration not found. Provide .streamlit/secrets.toml, env vars, or discogs_config.json")
    print("secrets.toml example:\n[discogs]\ntoken='...'\nuser_agent='...'\n# username='...'  # Optional\n[postgres]\nhost='localhost'\nport=5432\ndatabase='discogs_collection'\nuser='postgres'\npassword='postgres'\nschema='collection_data'")
    print("\nEnvironment variables: DISCOGS_TOKEN, DISCOGS_USERNAME (optional), POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, etc.")
    sys.exit(1)

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
    parser.add_argument('--wantlist-only', action='store_true', help='Download only the user\'s wantlist (wishlist)')
    parser.add_argument('--max-want-items', type=int, help='Limit number of wantlist items to download')
    parser.add_argument('--refresh-prices', action='store_true', help='Refresh marketplace prices and availability (uses scripts/refresh_prices_postgres.py)')
    parser.add_argument('--price-batch-limit', type=int, help='Limit number of releases to refresh prices for in one run')
    parser.add_argument('--refresh-stats', action='store_true', help='Refresh community statistics (have/want counts, ratings) for all releases')
    parser.add_argument('--stats-batch-limit', type=int, default=100, help='Limit number of releases to refresh stats for in one run (default 100)')
    parser.add_argument('--fix-country', action='store_true', help='Fix missing country values for releases only')
    parser.add_argument('--fix-country-batch', type=int, help='Limit number of releases to fix in one run (default 500)')
    parser.add_argument('--full-run', action='store_true', help='Download collection (incl. artwork), then refresh community stats and marketplace prices in one pass')
    parser.add_argument('--incremental-run', action='store_true', help='Download only recently added releases (last month), then refresh all stats and prices (fast update)')
    parser.add_argument('--refresh-release-stats', type=int, help='Refresh stats for a single release (discogs_release_id)')
    parser.add_argument('--ingest-sales-csv', type=str, help='Path to CSV to ingest historical sold stats (overwrites SCD1 dim)')
    parser.add_argument('--refresh-artist', type=str, help='Refresh detailed information for a specific artist by name')
    parser.add_argument('--refresh-artist-id', type=int, help='Refresh detailed information for a specific artist by Discogs ID')
    parser.add_argument('--refresh-all-artists', action='store_true', help='Refresh detailed information for all artists with missing data')
    parser.add_argument('--artist-batch-limit', type=int, help='Limit number of artists to refresh in one run')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # One-pass end-to-end workflow
    if args.full_run:
        logger.info("Starting full run: collection download + stats refresh + price refresh")
        try:
            downloader = DiscogsCollectionDownloader(config)
            # 1) Download collection (with artwork unless --no-artwork)
            downloader.download_collection(
                download_artwork=not args.no_artwork,
                max_releases=args.max_releases
            )
            # 2) Refresh community statistics (reconnect if needed)
            if not downloader.postgres.connection or downloader.postgres.connection.closed:
                downloader.postgres.connect()
            downloader.refresh_community_stats(batch_limit=args.stats_batch_limit)
            
            # 3) Refresh marketplace prices (via scripts/refresh_prices_postgres.py) and update marketplace_stats_dim as SCD1
            DiscogsCollectionDownloader.refresh_prices_via_script(batch_limit=args.price_batch_limit)
            
            # 4) Snapshot marketplace aggregates into marketplace_stats_dim (overwrite)
            try:
                # Ensure connection is active before marketplace stats update
                if not downloader.postgres.connection or downloader.postgres.connection.closed:
                    downloader.postgres.connect()
                    
                sql_upsert_dim = """
                INSERT INTO marketplace_stats_dim (discogs_release_id, last_sold_date, low_sold_price, high_sold_price, currency, as_of, notes)
                SELECT 
                    rp.discogs_release_id,
                    NULL::date AS last_sold_date,
                    CASE WHEN rp.lowest_price IS NOT NULL THEN rp.lowest_price END AS low_sold_price,
                    NULL::numeric AS high_sold_price,
                    rp.currency,
                    CURRENT_TIMESTAMP AS as_of,
                    'Populated from current marketplace stats; historical sold data not available via public API' AS notes
                FROM release_prices rp
                ON CONFLICT (discogs_release_id) DO UPDATE SET
                    last_sold_date = EXCLUDED.last_sold_date,
                    low_sold_price = EXCLUDED.low_sold_price,
                    high_sold_price = EXCLUDED.high_sold_price,
                    currency = EXCLUDED.currency,
                    as_of = EXCLUDED.as_of,
                    notes = EXCLUDED.notes
                """
                with downloader.postgres.connection.cursor() as cur:
                    cur.execute(sql_upsert_dim)
                downloader.postgres.connection.commit()
                logger.info("Successfully updated marketplace_stats_dim")
            except Exception as e:
                logger.warning(f"Failed to upsert marketplace_stats_dim: {e}")
        except KeyboardInterrupt:
            logger.info("Full run interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Full run failed: {e}")
            sys.exit(1)
        return
    
    # Incremental run - only process recently added releases, then full stats/price refresh
    if args.incremental_run:
        logger.info("Starting incremental run: recent releases only + full stats/price refresh")
        try:
            downloader = DiscogsCollectionDownloader(config)
            
            # 1) Download only recently added releases (last month)
            logger.info("Downloading only recently added releases (last month)")
            downloader.download_collection(
                download_artwork=not args.no_artwork,
                max_releases=args.max_releases or 50,  # Default limit for incremental
                incremental_mode=True  # We'll add this parameter
            )
            
            # 2) Refresh community statistics (reconnect if needed)
            if not downloader.postgres.connection or downloader.postgres.connection.closed:
                downloader.postgres.connect()
            downloader.refresh_community_stats(batch_limit=args.stats_batch_limit)
            
            # 3) Refresh marketplace prices
            DiscogsCollectionDownloader.refresh_prices_via_script(batch_limit=args.price_batch_limit)
            
            # 4) Update marketplace stats dimension
            try:
                if not downloader.postgres.connection or downloader.postgres.connection.closed:
                    downloader.postgres.connect()
                    
                sql_upsert_dim = """
                INSERT INTO marketplace_stats_dim (discogs_release_id, last_sold_date, low_sold_price, high_sold_price, currency, as_of, notes)
                SELECT 
                    rp.discogs_release_id,
                    NULL::date AS last_sold_date,
                    CASE WHEN rp.lowest_price IS NOT NULL THEN rp.lowest_price END AS low_sold_price,
                    NULL::numeric AS high_sold_price,
                    rp.currency,
                    CURRENT_TIMESTAMP AS as_of,
                    'Populated from current marketplace stats; historical sold data not available via public API' AS notes
                FROM release_prices rp
                ON CONFLICT (discogs_release_id) DO UPDATE SET
                    last_sold_date = EXCLUDED.last_sold_date,
                    low_sold_price = EXCLUDED.low_sold_price,
                    high_sold_price = EXCLUDED.high_sold_price,
                    currency = EXCLUDED.currency,
                    as_of = EXCLUDED.as_of,
                    notes = EXCLUDED.notes
                """
                with downloader.postgres.connection.cursor() as cur:
                    cur.execute(sql_upsert_dim)
                downloader.postgres.connection.commit()
                logger.info("Successfully updated marketplace_stats_dim")
            except Exception as e:
                logger.warning(f"Failed to upsert marketplace_stats_dim: {e}")
                
            logger.info("Incremental run completed successfully!")
        except KeyboardInterrupt:
            logger.info("Incremental run interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Incremental run failed: {e}")
            sys.exit(1)
        return
    
    if args.refresh_prices:
        try:
            DiscogsCollectionDownloader.refresh_prices_via_script(batch_limit=args.price_batch_limit)
        except Exception:
            sys.exit(1)
        # Only fetch prices and exit
        return
    
    if args.refresh_release_stats:
        downloader = DiscogsCollectionDownloader(config)
        try:
            # Community
            downloader.refresh_community_stats_for_release(args.refresh_release_stats)
            # Marketplace
            downloader.refresh_marketplace_for_release(args.refresh_release_stats)
        except Exception as e:
            logger.error(f"Per-release refresh failed: {e}")
            sys.exit(1)
        return
    
    # Artist refresh options
    if args.refresh_artist or args.refresh_artist_id or args.refresh_all_artists:
        downloader = DiscogsCollectionDownloader(config)
        try:
            if args.refresh_artist:
                logger.info(f"Refreshing artist details for: {args.refresh_artist}")
                success = downloader.refresh_artist_details(artist_name=args.refresh_artist)
                if success:
                    logger.info("Artist refresh completed successfully")
                else:
                    logger.error("Artist refresh failed")
                    sys.exit(1)
            
            elif args.refresh_artist_id:
                logger.info(f"Refreshing artist details for ID: {args.refresh_artist_id}")
                success = downloader.refresh_artist_details(artist_id=args.refresh_artist_id)
                if success:
                    logger.info("Artist refresh completed successfully")
                else:
                    logger.error("Artist refresh failed")
                    sys.exit(1)
            
            elif args.refresh_all_artists:
                logger.info(f"Refreshing all artists with missing data (batch size: {args.artist_batch_limit})")
                success = downloader.refresh_all_artists(batch_size=args.artist_batch_limit)
                if success:
                    logger.info("All artists refresh completed successfully")
                else:
                    logger.error("All artists refresh failed")
                    sys.exit(1)
                    
        except Exception as e:
            logger.error(f"Artist refresh failed: {e}")
            sys.exit(1)
        return

    if args.ingest_sales_csv:
        downloader = DiscogsCollectionDownloader(config)
        try:
            cnt = downloader.ingest_marketplace_sales_csv(args.ingest_sales_csv)
            logger.info(f"Ingested {cnt} rows into marketplace_stats_dim from CSV")
        except Exception as e:
            logger.error(f"CSV ingest failed: {e}")
            sys.exit(1)
        return

    if args.refresh_stats:
        try:
            downloader = DiscogsCollectionDownloader(config)
            downloader.refresh_community_stats(batch_limit=args.stats_batch_limit)
        except Exception as e:
            logger.error(f"Error refreshing community statistics: {e}")
            sys.exit(1)
        # Only refresh stats and exit
        return
    
    if args.fix_country:
        downloader = DiscogsCollectionDownloader(config)
        try:
            downloader.fix_missing_country(batch_limit=(args.fix_country_batch or 500))
        except Exception as e:
            logger.error(f"Fix country failed: {e}")
            sys.exit(1)
        return
    elif args.wantlist_only:
        logger.info("Running in wantlist-only mode")
        try:
            downloader = DiscogsCollectionDownloader(config)
            downloader.download_wantlist(max_items=args.max_want_items)
        except Exception as e:
            logger.error(f"Wantlist download failed: {e}")
            sys.exit(1)
    elif args.photos_only:
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