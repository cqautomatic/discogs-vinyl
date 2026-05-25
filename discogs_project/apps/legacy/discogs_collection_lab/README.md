# Discogs Collection Lab

## Overview
Build a comprehensive music collection management system using Snowflake and the Discogs API. This lab demonstrates how to download, store, and analyze your personal music collection data with advanced analytics and visualizations.

## Features
- 🎵 **Complete Collection Download**: Fetch your entire Discogs collection via API
- 🖼️ **Artwork Management**: Download and store album artwork locally and in Snowflake stages
- 📊 **Advanced Analytics**: Genre analysis, decade trends, artist insights, and collection statistics
- 🔍 **Smart Search**: Full-text search across your collection with relevance scoring
- 📱 **Interactive Dashboard**: Beautiful Streamlit interface for exploring your music
- ❄️ **Snowflake Integration**: Enterprise-grade data storage with SQL analytics

## Prerequisites
- Snowflake account with appropriate permissions
- Discogs account and API token
- Python 3.8 or higher
- Basic familiarity with SQL and Python

## Quick Start

### 1. Discogs API Setup
1. Create a Discogs account at [discogs.com](https://discogs.com)
2. Go to **Settings** → **Developers** → **Generate new token**
3. Copy your personal access token

### 2. Environment Setup
Create a `.env` file or set environment variables:

```bash
# Discogs Configuration
export DISCOGS_TOKEN="your_discogs_token_here"
export DISCOGS_USER_AGENT="YourApp/1.0 +http://yourwebsite.com"

# Snowflake Configuration
export SNOWFLAKE_ACCOUNT="your_account.region"
export SNOWFLAKE_USER="your_username"
export SNOWFLAKE_PASSWORD="your_password"
export SNOWFLAKE_WAREHOUSE="your_warehouse"
export SNOWFLAKE_DATABASE="DISCOGS_COLLECTION"
export SNOWFLAKE_SCHEMA="COLLECTION_DATA"
```

Or create a `discogs_config.json` file:

```json
{
    "token": "your_discogs_token_here",
    "user_agent": "YourApp/1.0 +http://yourwebsite.com",
    "snowflake_account": "your_account.region",
    "snowflake_user": "your_username", 
    "snowflake_password": "your_password",
    "snowflake_warehouse": "your_warehouse",
    "snowflake_database": "DISCOGS_COLLECTION",
    "snowflake_schema": "COLLECTION_DATA",
    "local_artwork_path": "./artwork",
    "rate_limit_delay": 1.0
}
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
Execute the setup script in Snowflake:

```sql
-- In Snowflake SQL worksheet, run:
-- Copy and paste contents of setup.sql
```

Or use the Snowflake CLI:
```bash
snowsql -f setup.sql
```

### 5. Download Your Collection
```bash
# Download complete collection with artwork
python discogs_downloader.py

# Download without artwork (faster)
python discogs_downloader.py --no-artwork

# Download only first 50 releases (for testing)
python discogs_downloader.py --max-releases 50
```

### 6. Launch the Dashboard
```bash
streamlit run streamlit_app.py
```

Access your collection dashboard at `http://localhost:8501`

## Database Schema

### Core Tables

#### `COLLECTIONS`
Main collection metadata
- `COLLECTION_ID`: Unique identifier
- `USERNAME`: Discogs username
- `TOTAL_ITEMS`: Total number of items in collection

#### `RELEASES`
Individual album/release information
- `RELEASE_ID`: Unique identifier
- `TITLE`, `ARTIST`, `YEAR`: Basic release info
- `GENRES`, `STYLES`: Musical categorization
- `RATING`, `CONDITION`: Personal ratings and condition
- `RAW_DATA`: Complete JSON from Discogs API

#### `ARTWORK`
Image files and metadata
- `ARTWORK_ID`: Unique identifier
- `ORIGINAL_URL`: Source URL from Discogs
- `LOCAL_FILE_PATH`: Local storage path
- `STAGE_FILE_PATH`: Snowflake stage path
- `IMAGE_WIDTH`, `IMAGE_HEIGHT`: Dimensions

### Views and Functions

#### `COLLECTION_STATS`
Comprehensive collection statistics including:
- Total items and download progress
- Unique artists, labels, countries
- Year range and rating averages
- Artwork file counts and sizes

#### `GENRE_ANALYSIS`
Genre-based analytics:
- Release counts per genre
- Average years and ratings
- Artist diversity per genre

#### `DECADE_ANALYSIS`
Time-based trends:
- Release distribution by decade
- Genre evolution over time
- Rating trends across eras

#### `SEARCH_COLLECTION(search_term)`
Full-text search function with relevance scoring across:
- Artist names
- Album titles
- Record labels
- Genres and styles

## Advanced Features

### Artwork Management
- Automatic download of cover art and additional images
- Local file storage with organized directory structure
- Snowflake stage integration for cloud storage
- Image metadata extraction (dimensions, file size)

### Data Analytics
- Genre distribution and trend analysis
- Decade-based collection insights
- Artist collaboration networks
- Label catalog analysis
- Condition and rating correlations

### Search Capabilities
- Multi-field search with relevance scoring
- Filter by year, country, condition, rating
- Genre and style-based filtering
- Advanced SQL-based search functions

## Dashboard Features

### 📊 Overview Page
- Key collection metrics
- Quick statistics and summaries
- Collection completion status
- Storage utilization

### 🎯 Genre Analysis
- Interactive genre distribution charts
- Top genres by various metrics
- Genre trend analysis over time
- Artist diversity per genre

### 📅 Decade Timeline
- Release distribution across decades
- Musical era preferences
- Rating trends over time
- Genre evolution visualization

### 🔍 Collection Browser
- Searchable release catalog
- Advanced filtering options
- Release detail cards with artwork
- Condition and rating displays

### 🎤 Artist Insights
- Top artists by collection size
- Artist rating analysis
- Collaboration networks
- Artist timeline presence

## Configuration Options

### Rate Limiting
Respect Discogs API limits (20 requests/minute):
```python
rate_limit_delay = 3.0  # 3 seconds between requests (safe)
```

### Artwork Settings
```python
local_artwork_path = "./artwork"  # Local storage directory
download_artwork = True           # Enable/disable artwork download
max_image_size = 5000000         # Maximum file size (5MB)
```

### Database Settings
```python
snowflake_database = "DISCOGS_COLLECTION"
snowflake_schema = "COLLECTION_DATA" 
artwork_stage = "ARTWORK_STAGE"
```

## Troubleshooting

### Common Issues

#### API Rate Limiting
- **Error**: `429 Too Many Requests`
- **Solution**: Increase `rate_limit_delay` or wait before retrying

#### Snowflake Connection
- **Error**: `Connection failed`
- **Solution**: Verify credentials and network connectivity
- Check account identifier format: `account.region.cloud`

#### Missing Dependencies
- **Error**: `ModuleNotFoundError`
- **Solution**: Install requirements: `pip install -r requirements.txt`

#### Artwork Download Failures
- **Error**: Image download timeouts
- **Solution**: Run with `--no-artwork` flag or check network

### Performance Optimization

#### Large Collections (1000+ releases)
- Use `--max-releases` for incremental downloads
- Run downloads during off-peak hours
- Consider chunked processing for very large collections

#### Snowflake Performance
- Use appropriate warehouse size for your data volume
- Consider data clustering for large tables
- Monitor credit usage during bulk operations

## API Reference

### Discogs API Endpoints Used
- `/oauth/identity` - User authentication
- `/users/{username}/collection/folders/0/releases` - Collection data
- `/releases/{release_id}` - Detailed release information
- `/masters/{master_id}` - Master release data
- `/artists/{artist_id}` - Artist information
- `/labels/{label_id}` - Label information

### Snowflake Objects Created
- **Database**: `DISCOGS_COLLECTION`
- **Schema**: `COLLECTION_DATA`
- **Stage**: `ARTWORK_STAGE`
- **Tables**: 6 main tables for normalized data storage
- **Views**: 3 analytical views for insights
- **Functions**: 1 search function with relevance scoring

## Data Privacy and Security

### Personal Data
- Collection data is stored in your private Snowflake account
- API tokens are stored in local configuration only
- No data is transmitted to third parties

### API Usage
- Respects Discogs rate limits and terms of service
- Uses official API endpoints only
- Includes proper attribution in user agent strings

## Contributing

This lab is part of the Snowflake Lab Generator project. To contribute:

1. Fork the repository
2. Create a feature branch
3. Add improvements or bug fixes
4. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review Discogs API documentation
- Consult Snowflake documentation for database issues

## License

This project is provided as-is for educational purposes. Please respect Discogs API terms of service and rate limits.

---

## Next Steps

After completing this lab, consider:

1. **Advanced Analytics**: Implement machine learning models for music recommendation
2. **Data Integration**: Connect additional music data sources (Spotify, Last.fm)
3. **Marketplace Analysis**: Add Discogs marketplace price tracking
4. **Social Features**: Compare collections with friends
5. **Mobile Interface**: Create a mobile-responsive dashboard

Happy collecting! 🎵