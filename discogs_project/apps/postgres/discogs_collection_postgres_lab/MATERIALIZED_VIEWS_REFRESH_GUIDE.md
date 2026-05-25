# Materialized Views Refresh Guide

## Overview

Your PostgreSQL materialized views (`collection_stats_mv`, `artwork_stats_mv`, etc.) **do not automatically update** when underlying data changes. This guide explains your refresh options.

## Current Refresh Methods ✅

### 1. Manual Refresh in Streamlit App
- **Location**: Sidebar "🔄 Refresh Data Views" button
- **When to use**: After viewing outdated data
- **Performance**: Immediate but requires manual action

### 2. Performance Dashboard
- **Location**: Performance tab → "🔄 Refresh Materialized Views" button  
- **When to use**: During maintenance or setup
- **Performance**: Manual, comprehensive refresh

### 3. Standalone Script
```bash
# Refresh all views manually
python refresh_views.py

# Quiet mode (for scripts/cron)
python refresh_views.py --quiet
```

## Recommended Refresh Strategies 🚀

### Strategy 1: Scheduled Refreshes (Recommended for Most Users)
**Best for**: Regular collection updates, balanced performance

```bash
# Add to crontab for every 30 minutes
*/30 * * * * cd /path/to/your/app && python refresh_views.py --quiet

# Or daily at 3 AM
0 3 * * * cd /path/to/your/app && python refresh_views.py --quiet
```

### Strategy 2: After Data Downloads
**Best for**: Immediate accuracy after imports

Add this to your data import workflow:
```bash
# After running discogs_downloader.py
python refresh_views.py
```

### Strategy 3: On-Demand Only
**Best for**: Small collections, infrequent updates
- Use the Streamlit sidebar button when data looks outdated
- Monitor data freshness manually

## Advanced Options 🔧

### Concurrent Refresh (Future Enhancement)
For high-traffic apps, consider adding `CONCURRENTLY` to refresh commands:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY collection_stats_mv;
```
*Note: Requires unique indexes on materialized views*

### Selective Refresh
You can modify `refresh_materialized_views()` to refresh only specific views:
```python
# In your code
refresh_materialized_views(db_conn, views_to_refresh=['collection_stats_mv'])
```

## Performance Considerations ⚡

| View | Refresh Time | Impact |
|------|-------------|---------|
| `collection_stats_mv` | ~1-5 seconds | Low |
| `artwork_stats_mv` | ~1-3 seconds | Low |
| `decade_analysis_mv` | ~2-10 seconds | Medium |
| `genre_analysis_mv` | ~5-30 seconds | Medium-High |
| `style_analysis_mv` | ~5-30 seconds | Medium-High |

## Monitoring Refresh Status 📊

### Check Last Refresh Time
Add this to your monitoring:
```sql
SELECT schemaname, matviewname, 
       (SELECT pg_stat_get_last_vacuum_time(oid)) as last_refreshed
FROM pg_matviews;
```

### Streamlit Data Freshness Indicator
Consider adding a "Last Updated" timestamp to your app interface.

## Troubleshooting 🔧

### View Doesn't Exist Error
```
ERROR: relation "collection_stats_mv" does not exist
```
**Solution**: Run the app once - it will create views automatically.

### Permission Errors
```
ERROR: permission denied for schema public
```
**Solution**: Ensure your database user has CREATE privileges.

### Refresh Fails
- Check database connectivity
- Verify underlying tables have data
- Check PostgreSQL logs for specific errors

## Recommendations Summary 📋

For **most users**:
1. ✅ Use the Streamlit sidebar refresh button when needed
2. ✅ Set up a daily cron job: `0 3 * * * python refresh_views.py --quiet`

For **heavy data users**:
1. ✅ Refresh after each data import
2. ✅ Consider hourly cron jobs: `0 * * * * python refresh_views.py --quiet`

For **development**:
1. ✅ Use manual refresh buttons in the app
2. ✅ Run `python refresh_views.py` after testing data changes

---

*Generated: $(date)*
*App: Discogs Collection Browser*

