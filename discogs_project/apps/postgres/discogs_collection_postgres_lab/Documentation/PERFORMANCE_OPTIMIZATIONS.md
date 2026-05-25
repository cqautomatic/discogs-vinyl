# Performance Optimizations

## Query Analysis and Improvements

### 1. Genre/Style Analysis Queries

**Original Issue**: Slow LATERAL joins for genre/style extraction
**Solution**: Add functional indexes and optimize queries

```sql
-- Add functional indexes for better performance
CREATE INDEX CONCURRENTLY idx_releases_genres_gin ON releases USING GIN (genres);
CREATE INDEX CONCURRENTLY idx_releases_styles_gin ON releases USING GIN (styles);

-- Optimized genre analysis query
CREATE OR REPLACE VIEW genre_analysis_optimized AS
SELECT 
    genre,
    COUNT(*) as release_count,
    COUNT(DISTINCT artist) as artist_count,
    AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre
WHERE genre IS NOT NULL AND genre != ''
GROUP BY genre
ORDER BY release_count DESC;
```

### 2. Decade Analysis Optimization

**Original Issue**: Slow generate_series with LEFT JOINs
**Solution**: Use materialized view for better performance

```sql
-- Create materialized view for decade analysis
CREATE MATERIALIZED VIEW decade_analysis_mv AS
WITH decade_series AS (
    SELECT generate_series(1950, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 10) AS decade
),
decade_counts AS (
    SELECT 
        (year / 10) * 10 AS decade,
        COUNT(*) as release_count
    FROM releases 
    WHERE year IS NOT NULL AND year >= 1950
    GROUP BY (year / 10) * 10
)
SELECT 
    ds.decade,
    COALESCE(dc.release_count, 0) as release_count
FROM decade_series ds
LEFT JOIN decade_counts dc ON ds.decade = dc.decade
ORDER BY ds.decade;

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_decade_analysis() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW decade_analysis_mv;
END;
$$ LANGUAGE plpgsql;
```

### 3. Collection Statistics Optimization

**Original Issue**: Multiple aggregations in single query
**Solution**: Break into smaller, cached queries

```sql
-- Create optimized statistics views
CREATE MATERIALIZED VIEW collection_stats_mv AS
SELECT 
    COUNT(*) as total_items,
    COUNT(CASE WHEN discogs_id IS NOT NULL THEN 1 END) as downloaded_items,
    COUNT(DISTINCT artist) as unique_artists,
    COUNT(DISTINCT label) as unique_labels,
    COUNT(DISTINCT country) as countries,
    MIN(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as earliest_year,
    MAX(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as latest_year,
    AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating,
    COUNT(CASE WHEN rating > 0 THEN 1 END) as rated_items
FROM releases;

CREATE MATERIALIZED VIEW artwork_stats_mv AS
SELECT 
    COUNT(*) as artwork_count,
    COALESCE(SUM(file_size), 0) as total_artwork_size_bytes
FROM artwork;
```

### 4. Search Query Optimization

**Original Issue**: Multiple LIKE operations without indexes
**Solution**: Add text search indexes

```sql
-- Add text search indexes
CREATE INDEX CONCURRENTLY idx_releases_title_gin ON releases USING GIN (to_tsvector('english', title));
CREATE INDEX CONCURRENTLY idx_releases_artist_gin ON releases USING GIN (to_tsvector('english', artist));
CREATE INDEX CONCURRENTLY idx_releases_label_gin ON releases USING GIN (to_tsvector('english', label));

-- Optimized search query using full-text search
CREATE OR REPLACE FUNCTION search_releases_optimized(search_term text)
RETURNS TABLE(
    release_id integer,
    title text,
    artist text,
    year integer,
    label text,
    catno text,
    format text,
    genres jsonb,
    styles jsonb,
    country text,
    rating integer,
    condition text,
    artwork_files json
) AS $$
BEGIN
    RETURN QUERY
    SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
           r.genres, r.styles, r.country, r.rating, r.condition,
           COALESCE(
               JSON_AGG(
                   JSON_BUILD_OBJECT(
                       'artwork_id', a.artwork_id,
                       'image_type', a.image_type,
                       'local_file_path', a.local_file_path,
                       'thumbnail_file_path', a.thumbnail_file_path,
                       'original_url', a.original_url
                   ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END
               ) FILTER (WHERE a.artwork_id IS NOT NULL),
               '[]'::json
           ) as artwork_files
    FROM releases r
    LEFT JOIN artwork a ON r.release_id = a.release_id
    WHERE 
        to_tsvector('english', r.title) @@ plainto_tsquery('english', search_term) OR
        to_tsvector('english', r.artist) @@ plainto_tsquery('english', search_term) OR
        to_tsvector('english', r.label) @@ plainto_tsquery('english', search_term)
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
             r.genres, r.styles, r.country, r.rating, r.condition
    ORDER BY r.artist, r.year;
END;
$$ LANGUAGE plpgsql;
```

### 5. Caching Strategy Improvements

**Application-Level Caching**:
- Increase cache TTL for static data (genres, decades)
- Implement cache warming for frequently accessed data
- Add cache invalidation triggers

```python
# Improved caching decorators
@st.cache_data(ttl=3600)  # 1 hour for static data
def load_genre_analysis_cached(_db_conn):
    return load_genre_analysis(_db_conn)

@st.cache_data(ttl=1800)  # 30 minutes for semi-static data
def load_decade_analysis_cached(_db_conn):
    return load_decade_analysis(_db_conn)

@st.cache_data(ttl=300)   # 5 minutes for dynamic data
def load_collection_stats_cached(_db_conn):
    return load_collection_stats(_db_conn)
```

### 6. Database Connection Optimization

**Connection Pooling**:
```python
# Implement connection pooling
from psycopg2 import pool

class OptimizedPostgreSQLConnection:
    _connection_pool = None
    
    @classmethod
    def get_pool(cls, config):
        if cls._connection_pool is None:
            cls._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
        return cls._connection_pool
    
    def get_connection(self):
        return self._connection_pool.getconn()
    
    def return_connection(self, conn):
        self._connection_pool.putconn(conn)
```

## Performance Monitoring

### 1. Query Performance Tracking
```sql
-- Enable query logging for analysis
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s
SELECT pg_reload_conf();
```

### 2. Index Usage Monitoring
```sql
-- Monitor index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'collection_data'
ORDER BY idx_scan DESC;
```

### 3. Performance Metrics Dashboard
```python
def display_performance_metrics(db_conn):
    """Display database performance metrics."""
    st.subheader("📊 Performance Metrics")
    
    # Query performance
    slow_queries = db_conn.execute_query("""
        SELECT query, calls, total_time, mean_time
        FROM pg_stat_statements
        WHERE mean_time > 100
        ORDER BY mean_time DESC
        LIMIT 10
    """)
    
    if slow_queries:
        st.dataframe(pd.DataFrame(slow_queries))
    
    # Cache hit ratios
    cache_stats = db_conn.execute_query("""
        SELECT 
            'Buffer Cache' as metric,
            ROUND(100.0 * sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)), 2) as hit_ratio
        FROM pg_statio_user_tables
        WHERE schemaname = 'collection_data'
    """)
    
    if cache_stats:
        st.metric("Cache Hit Ratio", f"{cache_stats[0]['hit_ratio']}%")
```

## Implementation Priority

1. **High Priority** (Immediate Impact):
   - Add GIN indexes for JSONB columns
   - Implement connection pooling
   - Optimize search queries with full-text search

2. **Medium Priority** (Significant Impact):
   - Create materialized views for expensive aggregations
   - Implement application-level caching improvements
   - Add query performance monitoring

3. **Low Priority** (Nice to Have):
   - Performance metrics dashboard
   - Advanced caching strategies
   - Query optimization based on usage patterns

## Expected Performance Improvements

- **Search Queries**: 60-80% faster with full-text search indexes
- **Genre/Style Analysis**: 40-60% faster with GIN indexes
- **Decade Analysis**: 70-90% faster with materialized views
- **Overall Application**: 30-50% faster response times
- **Database Load**: 20-40% reduction in CPU usage
