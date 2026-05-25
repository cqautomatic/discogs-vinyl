# Discogs Collection Lab (PostgreSQL Version)

## Overview
Build a comprehensive music collection management system using PostgreSQL and the Discogs API. This lab demonstrates how to download, store, and analyze your personal music collection data with advanced analytics and visualizations using the reliability and power of PostgreSQL.

Inspired by successful PostgreSQL implementations like [rezaisrad/discogs](https://github.com/rezaisrad/discogs) and [DylanBartels/discogs-load](https://github.com/DylanBartels/discogs-load), this version provides a complete solution for managing your Discogs collection with enterprise-grade PostgreSQL storage.

## Features
- 🎵 **Complete Collection Download**: Fetch your entire Discogs collection via API
- 🖼️ **Artwork Management**: Download and store album artwork locally with metadata tracking
- 📊 **Advanced Analytics**: Genre analysis, decade trends, artist insights, and collection statistics
- 🔍 **Smart Search**: Full-text search with PostgreSQL's powerful search capabilities
- 📱 **Interactive Dashboard**: Beautiful Streamlit interface for exploring your music
- 🐘 **PostgreSQL Integration**: Enterprise-grade data storage with JSONB support and advanced indexing

## Prerequisites
- PostgreSQL 12+ with extensions support
- Discogs account and API token
- Python 3.8 or higher
- Basic familiarity with SQL and Python

## Quick Start

### 1. Discogs API Setup
1. Create a Discogs account at [discogs.com](https://discogs.com)
2. Go to **Settings** → **Developers** → **Generate new token**
3. Copy your personal access token

### 2. PostgreSQL Setup

#### Option A: Local PostgreSQL Installation
```bash
# Install PostgreSQL (varies by OS)
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# macOS with Homebrew:
brew install postgresql

# Start PostgreSQL service
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS
```

#### Option B: Docker PostgreSQL
```bash
# Create and start PostgreSQL container
docker run --name discogs-postgres \
  -e POSTGRES_DB=discogs_collection \
  -e POSTGRES_USER=discogs_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -d postgres:15

# Or use docker-compose (create docker-compose.yml):
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: discogs_collection
      POSTGRES_USER: discogs_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 3. Environment Setup
Create a `.env` file or set environment variables:

```bash
# Discogs Configuration
export DISCOGS_TOKEN="your_discogs_token_here"
export DISCOGS_USER_AGENT="YourApp/1.0 +http://yourwebsite.com"

# PostgreSQL Configuration
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_USER="discogs_user"
export POSTGRES_PASSWORD="your_password"
export POSTGRES_DATABASE="discogs_collection"
export POSTGRES_SCHEMA="collection_data"
```

Or create a `discogs_config.json` file:

```json
{
    "token": "your_discogs_token_here",
    "user_agent": "YourApp/1.0 +http://yourwebsite.com",
    "postgres_host": "localhost",
    "postgres_port": 5432,
    "postgres_user": "discogs_user",
    "postgres_password": "your_password",
    "postgres_database": "discogs_collection",
    "postgres_schema": "collection_data",
    "local_artwork_path": "./artwork",
    "rate_limit_delay": 1.0
}
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Database Setup
Execute the setup script in PostgreSQL:

```bash
# Connect to PostgreSQL and run setup
psql -h localhost -U discogs_user -d discogs_collection -f setup.sql

# Or using environment variables
psql -f setup.sql
```

### 6. Download Your Collection
```bash
# Download complete collection with artwork
python discogs_downloader.py

# Download without artwork (faster)
python discogs_downloader.py --no-artwork

# Download only first 50 releases (for testing)
python discogs_downloader.py --max-releases 50
```

### 7. Launch the Interactive Collection Browser
```bash
streamlit run streamlit_app.py
```

Access your collection dashboard at `http://localhost:8501`

#### 🖼️ **NEW: Interactive Artwork Galleries**
Your collection browser now includes **multi-image support**:
- **Navigate between images** using ◀ ▶ arrow buttons  
- **Switch instantly** with thumbnail navigation
- **Smart fallback** from local files → URLs → placeholders
- **Image type labels** (primary, back, secondary, etc.)

**Usage**: Go to "Browse Collection" and click the arrows next to any artwork to cycle through all available images for that release!

## Database Schema

### Core Tables

#### `collections`
Main collection metadata
- `collection_id`: Unique identifier
- `username`: Discogs username
- `total_items`: Total number of items in collection

#### `releases`
Individual album/release information
- `release_id`: Unique identifier
- `title`, `artist`, `year`: Basic release info
- `genres`, `styles`: Musical categorization (JSONB arrays)
- `rating`, `condition`: Personal ratings and condition
- `raw_data`: Complete JSON from Discogs API (JSONB)

#### `artwork`
Image files and metadata
- `artwork_id`: Unique identifier
- `original_url`: Source URL from Discogs
- `local_file_path`: Local storage path
- `image_width`, `image_height`: Dimensions

### PostgreSQL-Specific Features

#### `JSONB` Support
All JSON data is stored using PostgreSQL's native JSONB type for:
- Efficient querying and indexing
- GIN indexes for fast JSON searches
- Direct JSON path queries

#### Views and Functions

##### `collection_stats`
Comprehensive collection statistics including:
- Total items and download progress
- Unique artists, labels, countries
- Year range and rating averages
- Artwork file counts and sizes

##### `genre_analysis`
Genre-based analytics using JSONB array expansion:
- Release counts per genre
- Average years and ratings
- Artist diversity per genre

##### `decade_analysis`
Time-based trends:
- Release distribution by decade
- Genre evolution over time
- Rating trends across eras

##### `search_collection(search_term)`
Basic search function with relevance scoring

##### `search_collection_fulltext(search_term)`
Advanced full-text search using PostgreSQL's text search:
- `to_tsvector` and `plainto_tsquery` for sophisticated matching
- Relevance ranking with `ts_rank`
- English language stemming and stop words

## Advanced Features

### Full-Text Search
PostgreSQL provides powerful full-text search capabilities:

```sql
-- Example: Search for "jazz fusion" with ranking
SELECT title, artist, ts_rank(to_tsvector('english', title || ' ' || artist), 
                               plainto_tsquery('english', 'jazz fusion')) as rank
FROM releases 
WHERE to_tsvector('english', title || ' ' || artist) @@ plainto_tsquery('english', 'jazz fusion')
ORDER BY rank DESC;
```

### JSONB Queries
Query JSON data directly:

```sql
-- Find all rock releases
SELECT title, artist FROM releases WHERE genres @> '["Rock"]';

-- Get all genres for a specific artist
SELECT DISTINCT jsonb_array_elements_text(genres) as genre 
FROM releases WHERE artist = 'Pink Floyd';
```

### GIN Indexes
The setup creates optimized indexes:
- Full-text search indexes on artist and title
- GIN indexes on JSONB columns (genres, styles)
- Composite indexes for common query patterns

### Triggers and Functions
Automatic timestamp updates using PostgreSQL triggers:
- `last_updated` fields automatically maintained
- Data integrity constraints
- Cleanup functions for orphaned records

## Dashboard Features

### 📊 Overview Page
- Key collection metrics with PostgreSQL aggregations
- Real-time statistics
- Collection completion status

### 🎯 Genre Analysis
- Interactive charts powered by JSONB queries
- Genre trend analysis over time
- Artist diversity per genre

### 📅 Decade Timeline
- Release distribution across decades
- Musical era preferences using date functions
- Rating trends over time

### 🔍 Collection Browser
- **Basic Search**: Simple pattern matching
- **Full-Text Search**: Advanced PostgreSQL text search
- Dynamic filtering with real-time queries
- Pagination and sorting

### 🎤 Artist Insights
- Top artists by collection size
- Artist rating analysis using window functions
- PostgreSQL analytics functions

## Performance Optimization

### Database Tuning
```sql
-- Recommended PostgreSQL settings for music collections
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;
SELECT pg_reload_conf();
```

### Indexing Strategy
The setup creates indexes optimized for common queries:
- B-tree indexes for exact matches (year, rating)
- GIN indexes for JSONB and full-text search
- Composite indexes for multi-column queries

### Query Optimization
- Use `EXPLAIN ANALYZE` to monitor query performance
- JSONB queries are optimized with GIN indexes
- Full-text search uses specialized text indexes

## Configuration Options

### Rate Limiting
Respect Discogs API limits (20 requests/minute):
```python
rate_limit_delay = 3.0  # 3 seconds between requests (safe)
```

### PostgreSQL Connection
```python
postgres_host = "localhost"      # Database host
postgres_port = 5432            # Database port
postgres_database = "discogs_collection"
postgres_schema = "collection_data"
```

### Artwork Settings
```python
local_artwork_path = "./artwork"  # Local storage directory
download_artwork = True           # Enable/disable artwork download
```

## Troubleshooting

### Common Issues

#### PostgreSQL Connection
- **Error**: `Connection refused`
- **Solution**: Ensure PostgreSQL is running and accessible
- Check `pg_hba.conf` for authentication settings

#### Permission Errors
- **Error**: `Permission denied for schema`
- **Solution**: Grant proper permissions:
```sql
GRANT USAGE ON SCHEMA collection_data TO discogs_user;
GRANT ALL ON ALL TABLES IN SCHEMA collection_data TO discogs_user;
```

#### JSONB Queries
- **Error**: Invalid JSON format
- **Solution**: Ensure JSON data is properly formatted
- Use `jsonb_pretty()` for debugging JSON content

#### Full-Text Search Issues
- **Error**: Text search not working
- **Solution**: Rebuild text search indexes:
```sql
REINDEX INDEX idx_releases_artist;
REINDEX INDEX idx_releases_title;
```

### Performance Optimization

#### Large Collections (1000+ releases)
- Monitor query performance with `EXPLAIN ANALYZE`
- Consider partitioning by decade for very large collections
- Use connection pooling for concurrent access

#### PostgreSQL Maintenance
```sql
-- Regular maintenance commands
VACUUM ANALYZE releases;
REINDEX DATABASE discogs_collection;
UPDATE pg_stat_statements_reset();
```

## Comparison with Other Implementations

This lab builds upon successful PostgreSQL implementations:

### vs. [rezaisrad/discogs](https://github.com/rezaisrad/discogs)
- ✅ **Similarities**: PostgreSQL storage, API integration
- 🔄 **Differences**: This lab focuses on personal collections vs. full discogs dumps
- ➕ **Additions**: Streamlit dashboard, full-text search, JSONB optimization

### vs. [DylanBartels/discogs-load](https://github.com/DylanBartels/discogs-load)
- ✅ **Similarities**: PostgreSQL as storage backend
- 🔄 **Differences**: API-based vs. XML dump loading
- ➕ **Additions**: Real-time API integration, interactive visualization

## API Reference

### Discogs API Endpoints Used
- `/oauth/identity` - User authentication
- `/users/{username}/collection/folders/0/releases` - Collection data
- `/releases/{release_id}` - Detailed release information
- `/masters/{master_id}` - Master release data
- `/artists/{artist_id}` - Artist information
- `/labels/{label_id}` - Label information

### PostgreSQL Objects Created
- **Database**: `discogs_collection`
- **Schema**: `collection_data`
- **Tables**: 6 main tables for normalized data storage
- **Views**: 3 analytical views for insights
- **Functions**: 2 search functions (basic and full-text)
- **Indexes**: Optimized for JSONB and text search

## Data Privacy and Security

### Personal Data
- Collection data is stored in your private PostgreSQL instance
- API tokens are stored in local configuration only
- No data is transmitted to third parties

### PostgreSQL Security
- Use strong passwords and proper authentication
- Configure `pg_hba.conf` for secure access
- Consider SSL connections for remote databases
- Regular backups with `pg_dump`

## Migration and Backup

### Backup Your Collection
```bash
# Full database backup
pg_dump discogs_collection > discogs_backup.sql

# Schema-only backup
pg_dump --schema-only discogs_collection > discogs_schema.sql

# Data-only backup
pg_dump --data-only discogs_collection > discogs_data.sql
```

### Restore from Backup
```bash
# Restore full backup
psql discogs_collection < discogs_backup.sql
```

## Contributing

This lab is part of the Snowflake Lab Generator project adapted for PostgreSQL. To contribute:

1. Fork the repository
2. Create a feature branch
3. Add improvements or bug fixes
4. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review PostgreSQL documentation for database issues
- Consult Discogs API documentation

## License

This project is provided as-is for educational purposes. Please respect Discogs API terms of service and rate limits.

---

## Next Steps

After completing this lab, consider:

1. **Performance Monitoring**: Set up monitoring with tools like pgAdmin or Grafana
2. **Data Analysis**: Use PostgreSQL's analytical functions for deeper insights
3. **API Integration**: Add real-time marketplace price tracking
4. **Scaling**: Implement read replicas for high-availability setups
5. **Advanced Search**: Implement fuzzy matching and similarity searches

Happy collecting with PostgreSQL! 🎵🐘