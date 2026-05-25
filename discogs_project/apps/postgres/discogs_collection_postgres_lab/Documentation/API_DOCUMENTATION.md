# API Documentation

## Core Modules

### core.config

Configuration management for the Discogs collection application.

#### Classes

##### `DiscogsConfig`
Configuration dataclass for application settings.

**Attributes:**
- `token: str` - Discogs API token
- `user_agent: str` - User agent for API requests
- `postgres_host: str` - PostgreSQL host
- `postgres_port: int` - PostgreSQL port
- `postgres_user: str` - PostgreSQL username
- `postgres_password: str` - PostgreSQL password
- `postgres_database: str` - PostgreSQL database name
- `postgres_schema: str` - PostgreSQL schema (default: "collection_data")
- `local_artwork_path: str` - Local artwork storage path (default: "./artwork")
- `username: Optional[str]` - Discogs username (optional)
- `rate_limit_delay: float` - API rate limit delay (default: 1.0)

#### Functions

##### `load_config() -> DiscogsConfig`
Load configuration from multiple sources in priority order:
1. `.streamlit/secrets.toml`
2. `discogs_config.json`
3. Environment variables

**Returns:** `DiscogsConfig` instance

**Example:**
```python
from core.config import load_config
config = load_config()
print(f"Token: {config.token}")
```

##### `validate_config(config: DiscogsConfig) -> bool`
Validate configuration for required fields.

**Parameters:**
- `config: DiscogsConfig` - Configuration to validate

**Returns:** `bool` - True if valid, False otherwise

### core.database

Database connection and query management.

#### Classes

##### `PostgreSQLConfig`
Configuration for PostgreSQL connections.

**Attributes:**
- `host: str` - Database host (default: "localhost")
- `port: int` - Database port (default: 5432)
- `user: str` - Database user (default: "discogs_user")
- `password: str` - Database password
- `database: str` - Database name (default: "discogs_collection")
- `schema: str` - Database schema (default: "collection_data")

##### `PostgreSQLConnection`
Manages PostgreSQL database connections with error handling.

**Methods:**

###### `__init__(config: Optional[PostgreSQLConfig] = None)`
Initialize database connection.

**Parameters:**
- `config: Optional[PostgreSQLConfig]` - Database configuration

###### `connect()`
Establish database connection with retry logic.

###### `execute_query(query: str, params=None) -> List[Dict]`
Execute SQL query with proper error handling.

**Parameters:**
- `query: str` - SQL query to execute
- `params: Optional[Tuple]` - Query parameters

**Returns:** `List[Dict]` - Query results as list of dictionaries

**Example:**
```python
from core.database import PostgreSQLConnection
db = PostgreSQLConnection()
results = db.execute_query("SELECT * FROM releases LIMIT 5")
```

#### Functions

##### `get_postgres_config_from_secrets_env() -> PostgreSQLConfig`
Load PostgreSQL configuration from Streamlit secrets or environment variables.

**Returns:** `PostgreSQLConfig` instance

### core.theme

Theme management for Streamlit application.

#### Functions

##### `apply_theme_css()`
Apply theme-aware CSS based on user selection. Creates a theme selector in the sidebar and applies appropriate CSS.

**Themes:**
- `auto` - Defaults to light theme
- `light` - Light theme with bright colors
- `dark` - Dark theme with muted colors

##### `get_current_theme() -> str`
Get the currently selected theme.

**Returns:** `str` - Current theme ('auto', 'light', or 'dark')

##### `is_dark_theme() -> bool`
Check if dark theme is currently active.

**Returns:** `bool` - True if dark theme is active

### core.utils

Utility functions for data processing and formatting.

#### Functions

##### `is_missing(value) -> bool`
Safely check if a value is missing/null, handling both scalar and array-like values.

**Parameters:**
- `value: Any` - Value to check

**Returns:** `bool` - True if value is missing/null

**Example:**
```python
from core.utils import is_missing
print(is_missing(None))  # True
print(is_missing(""))    # True
print(is_missing([]))    # True
print(is_missing("test")) # False
```

##### `get_color_map(items: List[str], color_scheme: str) -> Dict[str, str]`
Generate a color map for items based on the selected color scheme.

**Parameters:**
- `items: List[str]` - Items to assign colors to
- `color_scheme: str` - Color scheme ('Rainbow', 'Blue', 'Green', 'Red', 'Purple', 'Orange')

**Returns:** `Dict[str, str]` - Mapping of items to colors

##### `safe_int_conversion(value: Any, default: int = 0) -> int`
Safely convert a value to integer with fallback.

##### `safe_float_conversion(value: Any, default: float = 0.0) -> float`
Safely convert a value to float with fallback.

##### `format_large_number(num: int) -> str`
Format large numbers with appropriate suffixes (K, M, B).

##### `truncate_text(text: str, max_length: int = 50) -> str`
Truncate text to specified length with ellipsis.

##### `safe_json_loads(json_str: str, default=None)`
Safely parse JSON string with fallback.

##### `format_list_display(items: List[str], max_items: int = 3, separator: str = ", ") -> str`
Format a list for display with truncation.

## Data Layer

### data.queries

Centralized SQL queries for the application.

#### Query Constants

##### Collection Statistics
- `COLLECTION_STATS_QUERY` - Overall collection statistics
- `COLLECTION_VALUATION_QUERY` - Collection valuation data

##### Genre and Style Analysis
- `GENRE_ANALYSIS_QUERY` - Top genres with statistics
- `STYLE_ANALYSIS_QUERY` - Top styles with statistics
- `STYLES_FOR_GENRE_QUERY` - Styles within a specific genre
- `GENRES_FOR_STYLE_QUERY` - Genres within a specific style

##### Decade and Year Analysis
- `DECADE_ANALYSIS_QUERY` - Releases by decade with empty decades
- `YEAR_BREAKDOWN_QUERY` - Releases by year within a decade

##### Search and Browse
- `COLLECTION_SEARCH_QUERY` - Basic text search across collection
- `RANDOM_RELEASES_QUERY` - Random release selection with filters
- `RELEASES_FOR_YEAR_QUERY` - Releases for a specific year

##### Community Statistics
- `COMMUNITY_STATS_CHECK_QUERY` - Community statistics overview
- `MOST_POPULAR_RELEASES_QUERY` - Most popular releases by have count
- `MOST_WANTED_RELEASES_QUERY` - Most wanted releases by want count
- `HIGHEST_RATED_RELEASES_QUERY` - Highest rated releases

### data.loaders

Data loading functions with caching and optimization.

#### Functions

##### `load_collection_stats(_db_conn: PostgreSQLConnection) -> pd.DataFrame`
Load collection statistics with 30-minute caching.

**Parameters:**
- `_db_conn: PostgreSQLConnection` - Database connection

**Returns:** `pd.DataFrame` - Collection statistics

##### `load_genre_analysis(_db_conn: PostgreSQLConnection) -> pd.DataFrame`
Load genre analysis data with 1-hour caching.

##### `load_decade_analysis(_db_conn: PostgreSQLConnection) -> pd.DataFrame`
Load decade analysis data with 1-hour caching.

##### `search_collection(_db_conn: PostgreSQLConnection, search_term: str) -> pd.DataFrame`
Search collection with optimized full-text search if available.

**Parameters:**
- `_db_conn: PostgreSQLConnection` - Database connection
- `search_term: str` - Search term

**Returns:** `pd.DataFrame` - Search results

##### `load_random_releases(_db_conn: PostgreSQLConnection, count: int = 25, decade_start: int | None = None, rand_token: int = 0) -> pd.DataFrame`
Load random releases with optional decade filter.

**Parameters:**
- `_db_conn: PostgreSQLConnection` - Database connection
- `count: int` - Number of releases to return (default: 25)
- `decade_start: int | None` - Optional decade filter
- `rand_token: int` - Random seed for consistent results (default: 0)

**Returns:** `pd.DataFrame` - Random releases

### data.performance

Performance optimization utilities.

#### Functions

##### `create_performance_indexes(db_conn: PostgreSQLConnection) -> bool`
Create performance indexes for better query performance.

**Indexes Created:**
- GIN indexes for JSONB columns (genres, styles, producers)
- Full-text search indexes for title, artist, label
- Regular indexes for common queries (year, rating, discogs_id)
- Community statistics indexes

##### `create_materialized_views(db_conn: PostgreSQLConnection) -> bool`
Create materialized views for expensive queries.

**Views Created:**
- `collection_stats_mv` - Collection statistics
- `artwork_stats_mv` - Artwork statistics
- `decade_analysis_mv` - Decade analysis
- `genre_analysis_mv` - Genre analysis
- `style_analysis_mv` - Style analysis

##### `refresh_materialized_views(db_conn: PostgreSQLConnection) -> bool`
Refresh all materialized views.

##### `setup_performance_optimizations(db_conn: PostgreSQLConnection) -> dict`
Set up all performance optimizations and return status.

**Returns:** `dict` - Status of each optimization type

##### `display_performance_dashboard(db_conn: PostgreSQLConnection)`
Display performance optimization dashboard in Streamlit.

## Usage Examples

### Basic Setup

```python
from core.config import load_config
from core.database import PostgreSQLConnection
from data.loaders import load_collection_stats

# Load configuration
config = load_config()

# Create database connection
db = PostgreSQLConnection()

# Load data
stats = load_collection_stats(db)
print(f"Total releases: {stats.iloc[0]['total_items']}")
```

### Performance Optimization

```python
from data.performance import setup_performance_optimizations

# Set up all performance optimizations
results = setup_performance_optimizations(db)

if all(results.values()):
    print("All optimizations applied successfully!")
else:
    print("Some optimizations failed:", results)
```

### Theme Management

```python
from core.theme import apply_theme_css, is_dark_theme

# Apply theme CSS (call in Streamlit app)
apply_theme_css()

# Check current theme
if is_dark_theme():
    print("Dark theme is active")
```

### Search and Browse

```python
from data.loaders import search_collection, load_random_releases

# Search collection
results = search_collection(db, "Pink Floyd")
print(f"Found {len(results)} releases")

# Load random releases from 1970s
random_70s = load_random_releases(db, count=10, decade_start=1970)
print(f"Random 1970s releases: {len(random_70s)}")
```

## Error Handling

All functions include proper error handling:

- Database connection failures are logged and handled gracefully
- Query errors return empty DataFrames or None
- Configuration loading falls back through multiple sources
- Performance optimizations degrade gracefully if features are unavailable

## Caching Strategy

The application uses Streamlit's caching with different TTL values:

- **Static data** (genres, decades): 1 hour cache
- **Semi-static data** (collection stats): 30 minutes cache
- **Dynamic data** (search results): No caching
- **Performance stats**: 1 hour cache

## Performance Considerations

- Use materialized views for expensive aggregations
- Implement full-text search for better search performance
- Add appropriate indexes for common query patterns
- Use connection pooling for high-traffic scenarios
- Cache frequently accessed data at the application level
