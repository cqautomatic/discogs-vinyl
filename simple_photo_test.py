#!/usr/bin/env python3
"""
Simple test for the photo downloader functionality without PostgreSQL dependency.
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleArtworkDownloader:
    """Simplified artwork downloader for testing."""
    
    def __init__(self, local_path: str = "./test_artwork"):
        self.local_path = Path(local_path)
        self.local_path.mkdir(parents=True, exist_ok=True)
        self.session = self._create_session()
        
        # Configuration
        self.max_retries = 5
        self.base_retry_delay = 2.0
        self.max_retry_delay = 60.0
        self.jitter_percent = 0.2
        self.timeout = 30
        
        # Statistics
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'skipped_existing': 0
        }
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'DiscogsArtworkDownloader/1.0',
            'Accept': 'image/jpeg,image/png,image/gif,image/webp,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        return session
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
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
    
    def _validate_image_url(self, url: str) -> bool:
        """Validate that the URL looks like an image URL."""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        parsed = urlparse(url)
        if not parsed.netloc:
            return False
        
        # Check for common image extensions or known image domains
        path_lower = parsed.path.lower()
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff')
        
        has_image_ext = any(path_lower.endswith(ext) for ext in image_extensions)
        known_image_domains = ('i.discogs.com', 'img.discogs.com', 's.discogs.com', 'httpbin.org')
        is_image_domain = any(domain in parsed.netloc for domain in known_image_domains)
        
        return has_image_ext or is_image_domain
    
    def _generate_filename(self, image_url: str, release_id: str, image_type: str) -> str:
        """Generate a consistent filename for the image."""
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        
        parsed = urlparse(image_url)
        path_parts = parsed.path.split('.')
        file_extension = 'jpg'  # Default
        
        if len(path_parts) > 1:
            ext = path_parts[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                file_extension = ext
        
        clean_release_id = str(release_id).replace('/', '_').replace('\\', '_')
        clean_image_type = image_type.replace('/', '_').replace('\\', '_')
        
        return f"{clean_release_id}_{clean_image_type}_{url_hash}.{file_extension}"
    
    def download_image_with_retry(self, image_url: str, release_id: str, 
                                  image_type: str = "primary", 
                                  force_redownload: bool = False) -> Optional[Tuple[str, Dict]]:
        """Download an image with robust retry logic."""
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
            return self._get_file_metadata(local_file_path, image_url)
        
        # Attempt download with retries
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading {image_url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.session.get(image_url, stream=True, timeout=self.timeout)
                
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
                self.download_stats['successful'] += 1
                
                if attempt > 0:
                    self.download_stats['retried'] += 1
                
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
                self.download_stats['failed'] += 1
                return None
        
        # All retries failed
        logger.error(f"Failed to download {image_url} after {self.max_retries} attempts. Last error: {last_exception}")
        self.download_stats['failed'] += 1
        return None
    
    def _get_file_metadata(self, file_path: Path, original_url: str) -> Tuple[str, Dict]:
        """Get metadata for a downloaded file."""
        try:
            stat = file_path.stat()
            file_size = stat.st_size
            
            # Try to get image dimensions (optional)
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
    
    def get_stats(self) -> Dict[str, int]:
        """Get download statistics."""
        return self.download_stats.copy()

def test_downloads():
    """Test the photo downloader with various scenarios."""
    logger.info("=" * 60)
    logger.info("TESTING ENHANCED PHOTO DOWNLOADER")
    logger.info("=" * 60)
    
    downloader = SimpleArtworkDownloader()
    
    # Test URLs - using httpbin.org which provides test images
    test_cases = [
        {
            'name': 'Valid JPEG',
            'url': 'https://httpbin.org/image/jpeg',
            'release_id': 'test_release_1',
            'should_succeed': True
        },
        {
            'name': 'Valid PNG',
            'url': 'https://httpbin.org/image/png',
            'release_id': 'test_release_2',
            'should_succeed': True
        },
        {
            'name': 'Valid WebP',
            'url': 'https://httpbin.org/image/webp',
            'release_id': 'test_release_3',
            'should_succeed': True
        },
        {
            'name': '404 Not Found',
            'url': 'https://httpbin.org/status/404',
            'release_id': 'test_release_4',
            'should_succeed': False
        },
        {
            'name': '403 Forbidden',
            'url': 'https://httpbin.org/status/403',
            'release_id': 'test_release_5',
            'should_succeed': False
        },
        {
            'name': 'Invalid URL',
            'url': 'not_a_url',
            'release_id': 'test_release_6',
            'should_succeed': False
        },
        {
            'name': 'Non-existent domain',
            'url': 'https://this-domain-does-not-exist-12345.com/image.jpg',
            'release_id': 'test_release_7',
            'should_succeed': False
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        logger.info(f"\\nTesting: {test_case['name']}")
        logger.info(f"URL: {test_case['url']}")
        
        start_time = time.time()
        result = downloader.download_image_with_retry(
            test_case['url'],
            test_case['release_id'],
            'primary'
        )
        end_time = time.time()
        
        success = result is not None
        duration = end_time - start_time
        
        results.append({
            'name': test_case['name'],
            'expected': test_case['should_succeed'],
            'actual': success,
            'duration': duration,
            'result': result
        })
        
        if success == test_case['should_succeed']:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        
        logger.info(f"Result: {status} (took {duration:.2f}s)")
        if result:
            logger.info(f"  Downloaded: {result[0]}")
            logger.info(f"  Size: {result[1].get('file_size', 'unknown')} bytes")
    
    # Test existing file handling
    logger.info("\\n" + "=" * 40)
    logger.info("TESTING EXISTING FILE HANDLING")
    logger.info("=" * 40)
    
    test_url = 'https://httpbin.org/image/jpeg'
    
    # First download
    logger.info("\\nFirst download:")
    result1 = downloader.download_image_with_retry(test_url, 'existing_test', 'primary')
    
    # Second download (should skip)
    logger.info("\\nSecond download (should skip existing):")
    result2 = downloader.download_image_with_retry(test_url, 'existing_test', 'primary')
    
    # Force redownload
    logger.info("\\nForce redownload:")
    result3 = downloader.download_image_with_retry(test_url, 'existing_test', 'primary', force_redownload=True)
    
    # Print summary
    logger.info("\\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for r in results if r['expected'] == r['actual'])
    total = len(results)
    
    logger.info(f"Tests passed: {passed}/{total}")
    
    for result in results:
        status = "PASS" if result['expected'] == result['actual'] else "FAIL"
        logger.info(f"  {result['name']}: {status}")
    
    # Print download statistics
    stats = downloader.get_stats()
    logger.info(f"\\nDownload Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # Show downloaded files
    logger.info(f"\\nDownloaded files:")
    for file_path in downloader.local_path.glob("*"):
        if file_path.is_file():
            size = file_path.stat().st_size
            logger.info(f"  {file_path.name}: {size} bytes")

def cleanup():
    """Clean up test files."""
    test_dir = Path("./test_artwork")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
        logger.info("\\n✓ Cleaned up test directory")

def main():
    """Main test function."""
    try:
        test_downloads()
    except KeyboardInterrupt:
        logger.info("\\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()

if __name__ == '__main__':
    main()