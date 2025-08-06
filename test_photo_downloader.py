#!/usr/bin/env python3
"""
Test program for the enhanced artwork downloader.
Tests the download functionality with various scenarios.
"""

import sys
import logging
from pathlib import Path
from enhanced_artwork_downloader import RobustArtworkDownloader, DownloadConfig

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_download():
    """Test downloading a single image."""
    logger.info("=" * 50)
    logger.info("TEST 1: Single Image Download")
    logger.info("=" * 50)
    
    # Create test downloader
    config = DownloadConfig(
        local_artwork_path="./test_artwork",
        max_retries=3,
        base_retry_delay=1.0
    )
    downloader = RobustArtworkDownloader(config)
    
    # Test with a real Discogs image URL (this is a sample - replace with actual URL)
    test_urls = [
        "https://i.discogs.com/A-1234-1234567890.jpg",  # Sample Discogs URL format
        "https://httpbin.org/image/jpeg",  # Test service that returns a JPEG
        "https://httpbin.org/image/png",   # Test service that returns a PNG
    ]
    
    for i, test_url in enumerate(test_urls):
        logger.info(f"\nTesting download {i+1}: {test_url}")
        
        result = downloader.download_image_with_retry(
            image_url=test_url,
            release_id=f"test_release_{i+1}",
            image_type="primary"
        )
        
        if result:
            local_path, metadata = result
            logger.info(f"✓ Download successful: {local_path}")
            logger.info(f"  Metadata: {metadata}")
        else:
            logger.warning(f"✗ Download failed for {test_url}")
    
    # Print stats
    stats = downloader.get_stats()
    logger.info(f"\nDownload Statistics: {stats}")

def test_multiple_downloads():
    """Test downloading multiple images for a single release."""
    logger.info("\n" + "=" * 50)
    logger.info("TEST 2: Multiple Images for One Release")
    logger.info("=" * 50)
    
    config = DownloadConfig(local_artwork_path="./test_artwork")
    downloader = RobustArtworkDownloader(config)
    
    # Multiple test URLs
    artwork_urls = [
        "https://httpbin.org/image/jpeg",
        "https://httpbin.org/image/png", 
        "https://httpbin.org/image/webp",
    ]
    
    results = downloader.download_release_artwork(
        release_id="test_release_multi",
        artwork_urls=artwork_urls
    )
    
    logger.info(f"Downloaded {len(results)} out of {len(artwork_urls)} images")
    for local_path, metadata in results:
        logger.info(f"  ✓ {local_path}")
    
    stats = downloader.get_stats()
    logger.info(f"Updated Statistics: {stats}")

def test_error_handling():
    """Test error handling with invalid URLs."""
    logger.info("\n" + "=" * 50)
    logger.info("TEST 3: Error Handling")
    logger.info("=" * 50)
    
    config = DownloadConfig(
        local_artwork_path="./test_artwork",
        max_retries=2,
        base_retry_delay=0.5
    )
    downloader = RobustArtworkDownloader(config)
    
    # Test various error scenarios
    test_cases = [
        ("Invalid URL", "not_a_url"),
        ("404 Not Found", "https://httpbin.org/status/404"),
        ("403 Forbidden", "https://httpbin.org/status/403"),
        ("500 Server Error", "https://httpbin.org/status/500"),
        ("Non-existent domain", "https://this-domain-does-not-exist-12345.com/image.jpg"),
    ]
    
    for test_name, test_url in test_cases:
        logger.info(f"\nTesting {test_name}: {test_url}")
        
        result = downloader.download_image_with_retry(
            image_url=test_url,
            release_id="error_test",
            image_type="test"
        )
        
        if result:
            logger.warning(f"  Unexpected success for {test_name}")
        else:
            logger.info(f"  ✓ Correctly handled error for {test_name}")
    
    stats = downloader.get_stats()
    logger.info(f"Final Statistics: {stats}")

def test_existing_file_handling():
    """Test handling of existing files."""
    logger.info("\n" + "=" * 50)
    logger.info("TEST 4: Existing File Handling")
    logger.info("=" * 50)
    
    config = DownloadConfig(local_artwork_path="./test_artwork")
    downloader = RobustArtworkDownloader(config)
    
    test_url = "https://httpbin.org/image/jpeg"
    
    # First download
    logger.info("First download:")
    result1 = downloader.download_image_with_retry(
        image_url=test_url,
        release_id="existing_test",
        image_type="primary"
    )
    
    if result1:
        logger.info(f"  ✓ First download successful: {result1[0]}")
    
    # Second download (should skip existing)
    logger.info("\nSecond download (should skip existing):")
    result2 = downloader.download_image_with_retry(
        image_url=test_url,
        release_id="existing_test",
        image_type="primary"
    )
    
    if result2:
        logger.info(f"  ✓ Skipped existing file: {result2[0]}")
    
    # Force redownload
    logger.info("\nForce redownload:")
    result3 = downloader.download_image_with_retry(
        image_url=test_url,
        release_id="existing_test",
        image_type="primary",
        force_redownload=True
    )
    
    if result3:
        logger.info(f"  ✓ Force redownload successful: {result3[0]}")
    
    stats = downloader.get_stats()
    logger.info(f"Statistics: {stats}")

def test_cleanup():
    """Clean up test files."""
    logger.info("\n" + "=" * 50)
    logger.info("CLEANUP")
    logger.info("=" * 50)
    
    test_dir = Path("./test_artwork")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
        logger.info("✓ Cleaned up test directory")
    else:
        logger.info("No test directory to clean up")

def main():
    """Run all tests."""
    logger.info("Starting Enhanced Artwork Downloader Tests")
    
    try:
        test_single_download()
        test_multiple_downloads()
        test_error_handling()
        test_existing_file_handling()
        
        logger.info("\n" + "=" * 50)
        logger.info("ALL TESTS COMPLETED")
        logger.info("=" * 50)
        
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always cleanup
        test_cleanup()

if __name__ == '__main__':
    main()