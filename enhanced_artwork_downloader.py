#!/usr/bin/env python3
"""
Enhanced Artwork Downloader for Discogs Collection
Robust photo downloader with retry logic, exponential backoff, and proper error handling.
"""

import os
import sys
import time
import random
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from urllib.parse import urlparse
import psycopg2
import psycopg2.extras
from dataclasses import dataclass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('artwork_downloader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DownloadConfig:
    """Configuration for artwork downloading."""
    local_artwork_path: str = "./artwork"
    max_retries: int = 5
    base_retry_delay: float = 2.0  # Base delay in seconds
    max_retry_delay: float = 60.0  # Maximum delay between retries
    jitter_percent: float = 0.2  # Random variation percentage
    timeout: int = 30  # Request timeout in seconds
    chunk_size: int = 8192  # Download chunk size
    user_agent: str = "DiscogsArtworkDownloader/1.0"

class RobustArtworkDownloader:
    """Enhanced artwork downloader with retry logic and error handling."""
    
    def __init__(self, config: DownloadConfig = None):
        self.config = config or DownloadConfig()
        self.local_path = Path(self.config.local_artwork_path)
        self.local_path.mkdir(parents=True, exist_ok=True)
        self.session = self._create_session()
        
        # Statistics
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'skipped_existing': 0
        }
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers and timeouts."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'image/jpeg,image/png,image/gif,image/webp,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        return session
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Exponential backoff: base * (2 ^ attempt)
        delay = self.config.base_retry_delay * (2 ** attempt)
        
        # Cap at maximum delay
        delay = min(delay, self.config.max_retry_delay)
        
        # Add jitter (random variation)
        jitter = delay * self.config.jitter_percent * (2 * random.random() - 1)
        final_delay = delay + jitter
        
        # Ensure minimum delay
        return max(final_delay, 0.1)
    
    def _validate_image_url(self, url: str) -> bool:
        """Validate that the URL looks like an image URL."""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        parsed = urlparse(url)
        if not parsed.netloc:
            return False
        
        # Check for common image extensions
        path_lower = parsed.path.lower()
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff')
        
        # Either has image extension or is from known image domains
        has_image_ext = any(path_lower.endswith(ext) for ext in image_extensions)
        known_image_domains = ('i.discogs.com', 'img.discogs.com', 's.discogs.com')
        is_image_domain = any(domain in parsed.netloc for domain in known_image_domains)
        
        return has_image_ext or is_image_domain
    
    def _generate_filename(self, image_url: str, release_id: str, image_type: str) -> str:
        """Generate a consistent filename for the image."""
        # Create URL hash for uniqueness
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        
        # Extract file extension from URL
        parsed = urlparse(image_url)
        path_parts = parsed.path.split('.')
        file_extension = 'jpg'  # Default
        
        if len(path_parts) > 1:
            ext = path_parts[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                file_extension = ext
        
        # Clean release_id and image_type for filename
        clean_release_id = str(release_id).replace('/', '_').replace('\\', '_')
        clean_image_type = image_type.replace('/', '_').replace('\\', '_')
        
        return f"{clean_release_id}_{clean_image_type}_{url_hash}.{file_extension}"
    
    def _file_exists_and_valid(self, file_path: Path) -> bool:
        """Check if file exists and has valid size."""
        if not file_path.exists():
            return False
        
        try:
            # Check if file has reasonable size (not empty, not too small)
            file_size = file_path.stat().st_size
            return file_size > 1024  # At least 1KB
        except OSError:
            return False
    
    def download_image_with_retry(self, image_url: str, release_id: str, 
                                  image_type: str = "primary", 
                                  force_redownload: bool = False) -> Optional[Tuple[str, Dict]]:
        """
        Download an image with robust retry logic and error handling.
        
        Args:
            image_url: URL of the image to download
            release_id: ID of the release (for filename)
            image_type: Type of image (primary, secondary, etc.)
            force_redownload: Whether to redownload existing files
            
        Returns:
            Tuple of (local_file_path, metadata) or None if failed
        """
        # Validate URL
        if not self._validate_image_url(image_url):
            logger.warning(f"Invalid image URL: {image_url}")
            self.download_stats['failed'] += 1
            return None
        
        # Generate filename and path
        filename = self._generate_filename(image_url, release_id, image_type)
        local_file_path = self.local_path / filename
        
        # Check if file already exists
        if not force_redownload and self._file_exists_and_valid(local_file_path):
            logger.debug(f"Image already exists: {filename}")
            self.download_stats['skipped_existing'] += 1
            
            # Return existing file metadata
            return self._get_file_metadata(local_file_path, image_url)
        
        # Attempt download with retries
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Downloading {image_url} (attempt {attempt + 1}/{self.config.max_retries})")
                
                # Make request with timeout
                response = self.session.get(
                    image_url, 
                    stream=True, 
                    timeout=self.config.timeout
                )
                
                # Check response status
                if response.status_code == 404:
                    logger.warning(f"Image not found (404): {image_url}")
                    self.download_stats['failed'] += 1
                    return None
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403): {image_url}")
                    self.download_stats['failed'] += 1
                    return None
                elif response.status_code != 200:
                    raise requests.RequestException(f"HTTP {response.status_code}")
                
                # Validate content type
                content_type = response.headers.get('content-type', '').lower()
                if content_type and not content_type.startswith('image/'):
                    logger.warning(f"Invalid content type: {content_type} for {image_url}")
                    self.download_stats['failed'] += 1
                    return None
                
                # Download the file
                temp_file_path = local_file_path.with_suffix(f"{local_file_path.suffix}.tmp")
                bytes_downloaded = 0
                
                with open(temp_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                
                # Verify download
                if bytes_downloaded == 0:
                    temp_file_path.unlink(missing_ok=True)
                    raise ValueError("Downloaded file is empty")
                
                if bytes_downloaded < 1024:  # Less than 1KB might be an error page
                    logger.warning(f"Downloaded file suspiciously small: {bytes_downloaded} bytes")
                
                # Verify file is a valid image (optional, requires PIL)
                try:
                    from PIL import Image
                    with Image.open(temp_file_path) as img:
                        img.verify()  # Verify it's a valid image
                except ImportError:
                    pass  # PIL not available, skip verification
                except Exception as e:
                    logger.warning(f"Image verification failed: {e}")
                    # Continue anyway - might still be a valid image
                
                # Move temp file to final location
                temp_file_path.rename(local_file_path)
                
                # Success!
                logger.info(f"Successfully downloaded: {filename} ({bytes_downloaded} bytes)")
                self.download_stats['successful'] += 1
                
                if attempt > 0:
                    self.download_stats['retried'] += 1
                
                return self._get_file_metadata(local_file_path, image_url)
                
            except (requests.RequestException, OSError, ValueError) as e:
                last_exception = e
                logger.warning(f"Download attempt {attempt + 1} failed for {image_url}: {e}")
                
                # Clean up temp file if it exists
                temp_file_path = local_file_path.with_suffix(f"{local_file_path.suffix}.tmp")
                temp_file_path.unlink(missing_ok=True)
                
                # If this isn't the last attempt, wait before retrying
                if attempt < self.config.max_retries - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"Waiting {delay:.2f} seconds before retry...")
                    time.sleep(delay)
            
            except Exception as e:
                # Unexpected error - don't retry
                logger.error(f"Unexpected error downloading {image_url}: {e}")
                self.download_stats['failed'] += 1
                return None
        
        # All retries failed
        logger.error(f"Failed to download {image_url} after {self.config.max_retries} attempts. Last error: {last_exception}")
        self.download_stats['failed'] += 1
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
    
    def download_release_artwork(self, release_id: str, artwork_urls: List[str], 
                                force_redownload: bool = False) -> List[Tuple[str, Dict]]:
        """
        Download all artwork for a release.
        
        Args:
            release_id: ID of the release
            artwork_urls: List of image URLs to download
            force_redownload: Whether to redownload existing files
            
        Returns:
            List of (local_file_path, metadata) tuples for successful downloads
        """
        results = []
        
        for i, image_url in enumerate(artwork_urls):
            if not image_url:
                continue
                
            image_type = "primary" if i == 0 else f"image_{i}"
            
            try:
                result = self.download_image_with_retry(
                    image_url, 
                    release_id, 
                    image_type, 
                    force_redownload
                )
                
                if result:
                    results.append(result)
                
                # Rate limiting - small delay between downloads
                if i < len(artwork_urls) - 1:  # Don't sleep after last image
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error downloading artwork {i} for release {release_id}: {e}")
        
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """Get download statistics."""
        return self.download_stats.copy()
    
    def reset_stats(self):
        """Reset download statistics."""
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'skipped_existing': 0
        }

class PhotosOnlyDownloader:
    """Downloads only missing photos for existing releases in the database."""
    
    def __init__(self, postgres_config: dict, download_config: DownloadConfig = None):
        self.postgres_config = postgres_config
        self.downloader = RobustArtworkDownloader(download_config)
        self.connection = None
    
    def connect_to_database(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(**self.postgres_config)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def get_releases_without_artwork(self) -> List[Tuple[str, List[str]]]:
        """Get releases that don't have downloaded artwork."""
        if not self.connection:
            raise RuntimeError("Not connected to database")
        
        query = """
        SELECT DISTINCT r.release_id, r.artwork_urls
        FROM collection_data.releases r
        LEFT JOIN collection_data.artwork a ON r.release_id = a.release_id
        WHERE r.artwork_urls IS NOT NULL 
        AND r.artwork_urls != '[]'
        AND a.release_id IS NULL
        ORDER BY r.release_id
        """
        
        with self.connection.cursor() as cursor:
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
    
    def save_artwork_to_database(self, release_id: str, artwork_data: Dict):
        """Save artwork metadata to database."""
        if not self.connection:
            raise RuntimeError("Not connected to database")
        
        insert_query = """
        INSERT INTO collection_data.artwork 
        (artwork_id, release_id, image_type, original_url, local_file_path, 
         file_size, image_width, image_height, file_format, download_date)
        VALUES (%(artwork_id)s, %(release_id)s, %(image_type)s, %(original_url)s, 
                %(local_file_path)s, %(file_size)s, %(image_width)s, %(image_height)s, 
                %(file_format)s, %(download_date)s)
        ON CONFLICT (artwork_id) DO UPDATE SET
            local_file_path = EXCLUDED.local_file_path,
            file_size = EXCLUDED.file_size,
            image_width = EXCLUDED.image_width,
            image_height = EXCLUDED.image_height,
            file_format = EXCLUDED.file_format,
            download_date = EXCLUDED.download_date
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(insert_query, artwork_data)
        self.connection.commit()
    
    def download_missing_photos(self, force_redownload: bool = False, max_releases: Optional[int] = None):
        """Download missing photos for releases."""
        if not self.connection:
            self.connect_to_database()
        
        releases_to_download = self.get_releases_without_artwork()
        
        if max_releases:
            releases_to_download = releases_to_download[:max_releases]
        
        logger.info(f"Found {len(releases_to_download)} releases without artwork")
        
        for i, (release_id, artwork_urls) in enumerate(releases_to_download, 1):
            logger.info(f"Processing release {i}/{len(releases_to_download)}: {release_id}")
            
            try:
                results = self.downloader.download_release_artwork(
                    release_id, 
                    artwork_urls, 
                    force_redownload
                )
                
                # Save each downloaded artwork to database
                for j, (local_file_path, metadata) in enumerate(results):
                    image_type = "primary" if j == 0 else f"image_{j}"
                    
                    artwork_data = {
                        'artwork_id': f"artwork_{release_id}_{j}",
                        'release_id': release_id,
                        'image_type': image_type,
                        **metadata
                    }
                    
                    self.save_artwork_to_database(release_id, artwork_data)
                
                logger.info(f"Downloaded {len(results)} images for release {release_id}")
                
            except Exception as e:
                logger.error(f"Error processing release {release_id}: {e}")
        
        # Print final stats
        stats = self.downloader.get_stats()
        logger.info(f"Download completed. Stats: {stats}")

def main():
    """Main entry point for the enhanced artwork downloader."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Enhanced Discogs Artwork Downloader')
    parser.add_argument('--photos-only', action='store_true', 
                       help='Only download missing photos for existing releases')
    parser.add_argument('--force-redownload', action='store_true',
                       help='Redownload existing files')
    parser.add_argument('--max-releases', type=int,
                       help='Maximum number of releases to process')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--test-url', help='Test download with a single URL')
    
    args = parser.parse_args()
    
    # Load PostgreSQL configuration
    postgres_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DATABASE', 'discogs_collection'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    if not all([postgres_config['user'], postgres_config['password']]):
        logger.error("Please set POSTGRES_USER and POSTGRES_PASSWORD environment variables")
        sys.exit(1)
    
    # Test mode
    if args.test_url:
        logger.info(f"Testing download with URL: {args.test_url}")
        downloader = RobustArtworkDownloader()
        result = downloader.download_image_with_retry(args.test_url, "test_release", "test")
        if result:
            logger.info(f"Test download successful: {result[0]}")
        else:
            logger.error("Test download failed")
        return
    
    # Photos-only mode
    if args.photos_only:
        logger.info("Running in photos-only mode")
        photos_downloader = PhotosOnlyDownloader(postgres_config)
        try:
            photos_downloader.download_missing_photos(
                force_redownload=args.force_redownload,
                max_releases=args.max_releases
            )
        except Exception as e:
            logger.error(f"Photos-only download failed: {e}")
            sys.exit(1)
    else:
        logger.info("Use --photos-only to download missing photos for existing releases")
        logger.info("Use --test-url <URL> to test download functionality")

if __name__ == '__main__':
    main()