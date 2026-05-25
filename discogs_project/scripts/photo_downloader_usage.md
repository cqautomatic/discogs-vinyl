# Enhanced Photo Downloader for PostgreSQL Discogs Collection

## Overview

This enhanced photo downloader addresses the issues with the original photo download functionality by implementing robust retry logic, exponential backoff, and proper error handling based on industry best practices.

## Key Features

### 🔄 **Robust Retry Logic**
- **Exponential backoff** with jitter to avoid thundering herd problems
- **5 configurable retry attempts** with intelligent delay calculation
- **Proper error classification** (404, 403, network errors, etc.)
- **Graceful handling** of temporary network issues

### 📸 **Enhanced Photo Download**
- **URL validation** and content type checking
- **Atomic downloads** using temporary files
- **File size validation** to detect error pages
- **Image format detection** and proper file extensions
- **Duplicate detection** to avoid redownloading existing files

### 🛠 **Command Line Options**
- `--photos-only` - Download only missing photos for existing releases
- `--force-redownload-photos` - Redownload existing photos
- `--max-releases` - Limit number of releases to process

## Installation

1. **Prerequisites:**
   ```bash
   pip install requests psycopg2-binary pillow
   ```

2. **Environment Variables:**
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_USER=your_username
   export POSTGRES_PASSWORD=your_password
   export POSTGRES_DATABASE=discogs_collection
   export DISCOGS_TOKEN=your_discogs_token
   ```

## Usage Examples

### 1. Download Missing Photos Only

```bash
# Download missing photos for all releases
python discogs_downloader.py --photos-only

# Download missing photos for first 50 releases
python discogs_downloader.py --photos-only --max-releases 50

# Force redownload all photos (useful if previous downloads failed)
python discogs_downloader.py --photos-only --force-redownload-photos
```

### 2. Normal Collection Download

```bash
# Download collection data and photos (default behavior)
python discogs_downloader.py

# Download collection data but skip photos
python discogs_downloader.py --no-artwork

# Download collection data and photos for first 100 releases
python discogs_downloader.py --max-releases 100
```

### 3. Test Photo Download Functionality

```bash
# Test the enhanced photo downloader with sample URLs
python simple_photo_test.py
```

## Features Comparison

| Feature | Original | Enhanced |
|---------|----------|----------|
| **Retry Logic** | ❌ None | ✅ Exponential backoff with jitter |
| **Error Handling** | ⚠️ Basic | ✅ Comprehensive (404, 403, network, etc.) |
| **File Validation** | ⚠️ Size only | ✅ Size, content type, format validation |
| **Atomic Downloads** | ❌ No | ✅ Temporary files prevent corruption |
| **Existing File Check** | ✅ Basic | ✅ Enhanced with size validation |
| **Photos-Only Mode** | ❌ No | ✅ CLI switch for missing photos |
| **Progress Tracking** | ⚠️ Limited | ✅ Detailed logging and statistics |
| **Rate Limiting** | ⚠️ Basic | ✅ Configurable delays and respectful requests |

## Error Handling

The enhanced downloader handles various error scenarios:

### **Network Errors**
- **Connection timeouts**: Retry with exponential backoff
- **DNS resolution failures**: Retry up to 5 times
- **Temporary network issues**: Intelligent retry with jitter

### **HTTP Errors**
- **404 Not Found**: Skip and log (no retries)
- **403 Forbidden**: Skip and log (no retries)  
- **503 Service Unavailable**: Retry with backoff
- **Other HTTP errors**: Retry with backoff

### **File System Errors**
- **Disk space issues**: Fail gracefully with error message
- **Permission errors**: Log and continue with next file
- **Corrupted downloads**: Validate and retry if needed

## Configuration

### **Retry Configuration**
```python
# In enhanced_artwork_downloader.py
max_retries = 5              # Maximum retry attempts
base_retry_delay = 2.0       # Base delay in seconds
max_retry_delay = 60.0       # Maximum delay between retries
jitter_percent = 0.2         # Random variation (20%)
timeout = 30                 # Request timeout in seconds
```

### **Download Paths**
```python
# Default artwork storage location
local_artwork_path = "./artwork"

# Files are named as: {release_id}_{image_type}_{url_hash}.{extension}
# Example: 12345_primary_a1b2c3d4.jpg
```

## Database Integration

### **Photos-Only Mode Query**
The photos-only mode finds releases without downloaded artwork:

```sql
SELECT DISTINCT r.release_id, r.artwork_urls
FROM collection_data.releases r
LEFT JOIN collection_data.artwork a ON r.release_id = a.release_id
WHERE r.artwork_urls IS NOT NULL 
AND r.artwork_urls != '[]'
AND a.release_id IS NULL
ORDER BY r.release_id
```

### **Artwork Metadata Storage**
Downloaded artwork metadata is stored in the `artwork` table:

```sql
CREATE TABLE collection_data.artwork (
    artwork_id VARCHAR PRIMARY KEY,
    release_id VARCHAR,
    image_type VARCHAR,
    original_url TEXT,
    local_file_path TEXT,
    file_size INTEGER,
    image_width INTEGER,
    image_height INTEGER,
    file_format VARCHAR,
    download_date TIMESTAMP
);
```

## Performance Optimizations

### **Rate Limiting**
- **0.5 second delay** between image downloads
- **Respectful User-Agent** headers
- **Keep-alive connections** for efficiency

### **Network Optimizations**
- **Session reuse** with proper headers
- **Streaming downloads** for large files
- **Chunk-based writing** (8KB chunks)
- **Content-Type validation** before download

### **File System Optimizations**
- **Atomic writes** using temporary files
- **Duplicate detection** before download
- **Size validation** to avoid corrupted files
- **Proper file extensions** based on content

## Troubleshooting

### **Common Issues**

1. **"All downloads failing"**
   - Check internet connection
   - Verify Discogs API is accessible
   - Check if IP is rate-limited

2. **"Database connection errors"**
   - Verify PostgreSQL credentials
   - Check database is running
   - Ensure schema exists

3. **"Files downloading but corrupted"**
   - Check disk space
   - Verify file permissions
   - Review PIL installation for image validation

### **Debug Logging**
Enable detailed logging by setting log level:

```python
logging.basicConfig(level=logging.DEBUG)
```

### **Testing Individual URLs**
Test specific image URLs:

```bash
python enhanced_artwork_downloader.py --test-url "https://i.discogs.com/example.jpg"
```

## Migration from Original Downloader

1. **Backup existing data:**
   ```bash
   pg_dump discogs_collection > backup.sql
   ```

2. **Update the downloader:**
   - Replace `discogs_downloader.py` with enhanced version
   - No database schema changes required

3. **Download missing photos:**
   ```bash
   python discogs_downloader.py --photos-only
   ```

The enhanced downloader is fully backward compatible and will work with existing data.

## Performance Monitoring

### **Download Statistics**
The downloader tracks:
- `successful`: Successfully downloaded images
- `failed`: Failed downloads after all retries
- `retried`: Downloads that required retries
- `skipped_existing`: Files that already existed

### **Log Analysis**
Monitor log files for:
- Average download times
- Retry patterns
- Error frequency
- Network performance

This enhanced photo downloader provides a robust, production-ready solution for downloading Discogs artwork with proper error handling and retry logic.