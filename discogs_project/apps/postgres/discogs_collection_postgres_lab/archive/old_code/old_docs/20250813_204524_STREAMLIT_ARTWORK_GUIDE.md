# Streamlit Collection Browser with Artwork Galleries

## Overview

Your Discogs collection browser now includes **interactive artwork galleries** that allow you to browse through multiple images for each album. The app displays your collection with all downloaded artwork and provides seamless navigation between images.

## Key Features

### 🖼️ **Multi-Image Support**
- Each release can display **multiple artwork images** (primary, secondary, back cover, etc.)
- **Navigate between images** using ◀ ▶ arrow buttons
- **Image counter** shows current position (e.g., "2 of 4")
- **Thumbnail navigation** for quick jumping between images (when ≤5 images)

### 📷 **Smart Image Display**
- **Priority order**: Local downloaded files → Original URLs → Placeholder
- **Image types labeled**: Primary, secondary, back, etc.
- **Automatic fallback** if local files are missing
- **Error handling** for broken image URLs

### 🔍 **Enhanced Collection Browser**
- **Real-time search** across artist, title, label, and genres
- **Artwork integration** in all views
- **Genre tags** with visual styling
- **Rating display** with star ratings
- **Condition information** for collectors

## How to Use

### Starting the App

```bash
# Navigate to your lab directory
cd generated_labs/discogs_collection_postgres_lab

# Start the Streamlit app
streamlit run streamlit_app.py
```

### Browsing Your Collection

1. **Navigate to "Browse Collection"** in the sidebar
2. **Search (optional)**: Enter artist, album, label, or genre in the search box
3. **View artwork**: Each release shows its artwork in an interactive gallery
4. **Switch images**: Use ◀ ▶ buttons to navigate between multiple images
5. **Quick thumbnails**: Click 📷 buttons for instant image switching

### Image Navigation Controls

| Control | Function |
|---------|----------|
| ◀ Button | Previous image |
| ▶ Button | Next image |
| Image counter | Shows "X of Y" position |
| 📷 Thumbnails | Quick jump to specific image |
| Expand "🖼️ All Images" | See thumbnail grid |

## Database Integration

### Artwork Data Sources

The app retrieves artwork from **two complementary sources**:

1. **`artwork` table**: Individual image records with metadata
   ```sql
   SELECT artwork_id, image_type, local_file_path, original_url, 
          file_size, image_width, image_height
   FROM artwork WHERE release_id = 'release_123'
   ```

2. **`releases.local_artwork_paths`**: JSONB array of file paths
   ```sql
   SELECT local_artwork_paths FROM releases WHERE release_id = 'release_123'
   ```

### Query Optimization

The app uses **optimized PostgreSQL queries** with:
- **LEFT JOIN** between releases and artwork tables
- **JSON aggregation** for multiple images per release
- **ORDER BY** for consistent primary image display
- **Efficient indexing** on release_id foreign keys

## Image Display Logic

### Priority Order
```python
1. Try local_file_path (if file exists on disk)
2. Fallback to original_url (if accessible)
3. Final fallback to placeholder image
```

### Error Handling
- **Missing local files**: Automatically tries original URL
- **Broken URLs**: Shows placeholder with error message
- **No artwork**: Displays "No Image Available" placeholder
- **Gallery state**: Persists image position during navigation

## Supported Image Types

The app recognizes and labels these image types:
- **`primary`**: Main album cover (displayed first)
- **`secondary`**: Alternative covers
- **`back`**: Back cover artwork
- **`image_1`, `image_2`, etc.**: Additional images

## Performance Features

### Caching
- **@st.cache_data**: Database queries cached for faster loading
- **Session state**: Gallery positions maintained during browsing
- **Clear cache**: Available in sidebar for data refresh

### Responsive Design
- **Column layouts**: Optimized for different screen sizes
- **Image sizing**: Consistent 150px width for gallery view
- **Mobile friendly**: Touch-friendly navigation buttons

## Troubleshooting

### No Images Displayed
1. **Check artwork download**: Run `python discogs_downloader.py --photos-only`
2. **Verify file paths**: Ensure downloaded images exist on disk
3. **Database connection**: Confirm PostgreSQL connection in sidebar
4. **Clear cache**: Use "🔄 Clear Cache" button in sidebar

### Image Navigation Not Working
1. **Check browser JavaScript**: Ensure JavaScript is enabled
2. **Session state**: Try refreshing the page
3. **Multiple instances**: Close other browser tabs with the app

### Database Connection Issues
```bash
# Test your PostgreSQL connection
python test_connection.py

# Check if tables exist
psql -d discogs_collection -c "\dt collection_data.*"
```

## Example Usage

### Typical Workflow
1. **Download collection**: `python discogs_downloader.py`
2. **Download artwork**: `python discogs_downloader.py --photos-only`
3. **Start browser**: `streamlit run streamlit_app.py`
4. **Browse and enjoy**: Navigate through your collection with full artwork!

### Search Examples
- Artist: "Pink Floyd"
- Album: "Dark Side"
- Label: "Capitol"
- Genre: "Rock"
- Year range filtering (coming soon)

## Integration with Discogs Downloader

The Streamlit app works seamlessly with the fixed downloader:
- **Foreign key constraints**: Proper release→artwork relationships
- **Multiple image support**: All images downloaded and linked
- **Metadata preservation**: File sizes, dimensions, types stored
- **Error resilience**: Individual image failures don't break collection

## Future Enhancements

Coming improvements:
- **Full-screen image viewer** with modal dialogs
- **Image comparison** side-by-side view
- **Download progress tracking** in real-time
- **Export functionality** for sharing collections
- **Advanced filtering** by year, rating, condition

---

**Your collection browser now provides a rich, interactive experience for exploring your music collection with full artwork support!** 🎵📷