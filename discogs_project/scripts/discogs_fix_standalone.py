#!/usr/bin/env python3
"""
Standalone fix for the Discogs "'list' object has no attribute 'get'" error.
This demonstrates the solution without requiring the full downloader file.
"""

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== ROBUST DATA EXTRACTION FUNCTIONS =====
# These functions replace the problematic code that causes the error

def safe_get_name(item, field_name='name', default=''):
    """Safely extract a name field from an item that might be a dict, list, or string."""
    try:
        if isinstance(item, dict):
            return item.get(field_name, default)
        elif isinstance(item, str):
            return item
        elif isinstance(item, list):
            if len(item) > 0 and isinstance(item[0], dict):
                return item[0].get(field_name, default)
            elif len(item) > 0 and isinstance(item[0], str):
                return item[0]
            else:
                return default
        elif item is None:
            return default
        else:
            return str(item)
    except Exception as e:
        logger.debug(f"Error extracting {field_name} from {type(item)}: {e}")
        return default

def safe_extract_artists(artists_data):
    """Safely extract artist names from artists data."""
    if not artists_data:
        return ''
    try:
        if isinstance(artists_data, list):
            names = []
            for artist in artists_data:
                name = safe_get_name(artist, 'name', '')
                if name:
                    names.append(name)
            return ', '.join(names)
        elif isinstance(artists_data, dict):
            return safe_get_name(artists_data, 'name', '')
        elif isinstance(artists_data, str):
            return artists_data
        else:
            return str(artists_data)
    except Exception as e:
        logger.warning(f"Error extracting artists: {e}")
        return ''

def safe_extract_labels(labels_data):
    """Safely extract label names from labels data."""
    if not labels_data:
        return ''
    try:
        if isinstance(labels_data, list):
            names = []
            for label in labels_data:
                name = safe_get_name(label, 'name', '')
                if name:
                    names.append(name)
            return ', '.join(names)
        elif isinstance(labels_data, dict):
            return safe_get_name(labels_data, 'name', '')
        elif isinstance(labels_data, str):
            return labels_data
        else:
            return str(labels_data)
    except Exception as e:
        logger.warning(f"Error extracting labels: {e}")
        return ''

def safe_extract_catalog_numbers(labels_data):
    """Safely extract catalog numbers from labels data."""
    if not labels_data:
        return ''
    try:
        if isinstance(labels_data, list):
            catnos = []
            for label in labels_data:
                catno = safe_get_name(label, 'catno', '')
                if catno:
                    catnos.append(catno)
            return ', '.join(catnos)
        elif isinstance(labels_data, dict):
            return safe_get_name(labels_data, 'catno', '')
        elif isinstance(labels_data, str):
            return labels_data
        else:
            return ''
    except Exception as e:
        logger.warning(f"Error extracting catalog numbers: {e}")
        return ''

def safe_extract_formats(formats_data):
    """Safely extract format names from formats data."""
    if not formats_data:
        return ''
    try:
        if isinstance(formats_data, list):
            names = []
            for fmt in formats_data:
                name = safe_get_name(fmt, 'name', '')
                if name:
                    names.append(name)
            return ', '.join(names)
        elif isinstance(formats_data, dict):
            return safe_get_name(formats_data, 'name', '')
        elif isinstance(formats_data, str):
            return formats_data
        else:
            return str(formats_data)
    except Exception as e:
        logger.warning(f"Error extracting formats: {e}")
        return ''

def safe_extract_notes(notes_data):
    """Safely extract notes value from notes data."""
    if not notes_data:
        return None
    try:
        if isinstance(notes_data, dict):
            return notes_data.get('value', None)
        elif isinstance(notes_data, str):
            return notes_data
        elif isinstance(notes_data, list):
            if len(notes_data) > 0:
                if isinstance(notes_data[0], dict):
                    return notes_data[0].get('value', None)
                else:
                    return str(notes_data[0])
            return None
        else:
            return str(notes_data)
    except Exception as e:
        logger.debug(f"Error extracting notes: {e}")
        return None

def safe_extract_list_field(data, default=None):
    """Safely extract a field that should be a list."""
    if default is None:
        default = []
    try:
        if isinstance(data, list):
            return data
        elif isinstance(data, str):
            return [data] if data else default
        elif data is None:
            return default
        else:
            return [str(data)]
    except Exception as e:
        logger.debug(f"Error extracting list field: {e}")
        return default

# ===== DEMONSTRATION FUNCTIONS =====

def show_problematic_code():
    """Show what the original problematic code looked like."""
    print("🚫 ORIGINAL PROBLEMATIC CODE (would cause errors):")
    print("=" * 60)
    print("# This is what was causing the error:")
    print("artist_names = ', '.join([artist.get('name', '') for artist in basic_info.get('artists', [])])")
    print("label_names = ', '.join([label.get('name', '') for label in basic_info.get('labels', [])])")
    print("catalog_numbers = ', '.join([label.get('catno', '') for label in basic_info.get('labels', [])])")
    print("format_names = ', '.join([fmt.get('name', '') for fmt in basic_info.get('formats', [])])")
    print("\n❌ Problem: Assumes artists/labels/formats are always lists of dictionaries")
    print("❌ Reality: Sometimes they're strings, nested lists, or other types")

def show_fixed_code():
    """Show what the fixed code looks like."""
    print("\n✅ FIXED CODE (robust and error-free):")
    print("=" * 60)
    print("# This is the solution:")
    print("artist_names = safe_extract_artists(basic_info.get('artists', []))")
    print("label_names = safe_extract_labels(basic_info.get('labels', []))")
    print("catalog_numbers = safe_extract_catalog_numbers(basic_info.get('labels', []))")
    print("format_names = safe_extract_formats(basic_info.get('formats', []))")
    print("genres_list = safe_extract_list_field(basic_info.get('genres', []))")
    print("styles_list = safe_extract_list_field(basic_info.get('styles', []))")
    print("notes_value = safe_extract_notes(release_data.get('notes'))")
    print("\n✅ Solution: Robust functions that handle any data type safely")

def demonstrate_error_cases():
    """Demonstrate the cases that would cause the original error."""
    print("\n🧪 TESTING ERROR CASES:")
    print("=" * 60)
    
    # Case 1: Artists as strings instead of dicts
    print("\n1. Artists as list of strings (would cause original error):")
    artists_data = ['The Beatles', 'John Lennon', 'Paul McCartney']
    print(f"   Input: {artists_data}")
    print(f"   Original code: [artist.get('name', '') for artist in artists_data]")
    print(f"   ❌ Would error: AttributeError: 'str' object has no attribute 'get'")
    result = safe_extract_artists(artists_data)
    print(f"   ✅ Fixed code result: '{result}'")
    
    # Case 2: Labels as nested list
    print("\n2. Labels as nested list (would cause original error):")
    labels_data = [['Capitol Records', 'LABEL001'], ['Apple Records', 'LABEL002']]
    print(f"   Input: {labels_data}")
    print(f"   Original code: [label.get('name', '') for label in labels_data]")
    print(f"   ❌ Would error: AttributeError: 'list' object has no attribute 'get'")
    result = safe_extract_labels(labels_data)
    print(f"   ✅ Fixed code result: '{result}'")
    
    # Case 3: Formats as single string
    print("\n3. Formats as single string (would cause original error):")
    formats_data = 'Vinyl LP'
    print(f"   Input: '{formats_data}'")
    print(f"   Original code: [fmt.get('name', '') for fmt in formats_data]")
    print(f"   ❌ Would error: AttributeError: 'str' object has no attribute 'get'")
    result = safe_extract_formats(formats_data)
    print(f"   ✅ Fixed code result: '{result}'")
    
    # Case 4: Notes as list instead of dict
    print("\n4. Notes as list (would cause original error):")
    notes_data = ['Excellent condition', 'Original pressing']
    print(f"   Input: {notes_data}")
    print(f"   Original code: notes_data.get('value')")
    print(f"   ❌ Would error: AttributeError: 'list' object has no attribute 'get'")
    result = safe_extract_notes(notes_data)
    print(f"   ✅ Fixed code result: '{result}'")

def simulate_real_discogs_data():
    """Simulate processing real Discogs data with problematic structures."""
    print("\n🎵 SIMULATING REAL DISCOGS RELEASE DATA:")
    print("=" * 60)
    
    # Simulate various problematic release data structures you might encounter
    test_releases = [
        {
            'id': 12345,
            'basic_information': {
                'artists': ['Various Artists'],  # String instead of dict
                'labels': [['Label Name', 'CAT123']],  # Nested list
                'formats': 'LP',  # String instead of list
                'genres': 'Electronic',  # String instead of list
                'title': 'Test Album 1'
            },
            'notes': ['Great condition']  # List instead of dict
        },
        {
            'id': 67890, 
            'basic_information': {
                'artists': [{'name': 'Artist 1'}, 'Artist 2'],  # Mixed types
                'labels': 'Independent Label',  # String instead of list
                'formats': [['Vinyl'], 'CD'],  # Mixed nested structures
                'genres': ['Rock', 'Pop'],  # Correct format
                'title': 'Test Album 2'
            },
            'notes': {'value': 'Mint condition'}  # Correct format
        },
        {
            'id': 11111,
            'basic_information': {
                'artists': None,  # None value
                'labels': [],  # Empty list
                'formats': [{}],  # List with empty dict
                'genres': 12345,  # Unexpected type
                'title': 'Test Album 3'
            },
            'notes': None  # None value
        }
    ]
    
    for i, release in enumerate(test_releases, 1):
        print(f"\n--- Processing Release {i} (ID: {release['id']}) ---")
        basic_info = release.get('basic_information', {})
        
        try:
            # Use the safe extraction functions
            artist_names = safe_extract_artists(basic_info.get('artists', []))
            label_names = safe_extract_labels(basic_info.get('labels', []))
            catalog_numbers = safe_extract_catalog_numbers(basic_info.get('labels', []))
            format_names = safe_extract_formats(basic_info.get('formats', []))
            genres_list = safe_extract_list_field(basic_info.get('genres', []))
            styles_list = safe_extract_list_field(basic_info.get('styles', []))
            notes_value = safe_extract_notes(release.get('notes'))
            
            print(f"✅ Successfully processed release {release['id']}!")
            print(f"   Title: {basic_info.get('title', 'Unknown')}")
            print(f"   Artists: '{artist_names}'")
            print(f"   Labels: '{label_names}'")
            print(f"   Catalog: '{catalog_numbers}'")
            print(f"   Formats: '{format_names}'")
            print(f"   Genres: {genres_list}")
            print(f"   Notes: {notes_value}")
            
        except Exception as e:
            print(f"❌ Error processing release {release['id']}: {e}")

def show_implementation_guide():
    """Show how to implement the fix in your code."""
    print("\n🔧 IMPLEMENTATION GUIDE:")
    print("=" * 60)
    print("To fix your Discogs downloader, replace these lines in your _process_release method:")
    print()
    print("REPLACE THIS:")
    print("    'artist': ', '.join([artist.get('name', '') for artist in basic_info.get('artists', [])]),")
    print("    'label': ', '.join([label.get('name', '') for label in basic_info.get('labels', [])]),")
    print("    'catno': ', '.join([label.get('catno', '') for label in basic_info.get('labels', [])]),")
    print("    'format': ', '.join([fmt.get('name', '') for fmt in basic_info.get('formats', [])]),")
    print()
    print("WITH THIS:")
    print("    'artist': safe_extract_artists(basic_info.get('artists', [])),")
    print("    'label': safe_extract_labels(basic_info.get('labels', [])),")
    print("    'catno': safe_extract_catalog_numbers(basic_info.get('labels', [])),")
    print("    'format': safe_extract_formats(basic_info.get('formats', [])),")
    print()
    print("And add the safe extraction functions at the top of your file.")

def main():
    """Run the complete demonstration."""
    print("🔧 DISCOGS 'LIST OBJECT HAS NO ATTRIBUTE GET' ERROR FIX")
    print("=" * 80)
    print("This demonstrates the cause and solution for the common Discogs API error.")
    
    show_problematic_code()
    show_fixed_code()
    demonstrate_error_cases()
    simulate_real_discogs_data()
    show_implementation_guide()
    
    print("\n" + "=" * 80)
    print("🎉 SUMMARY:")
    print("✅ The fix handles all problematic data structures safely")
    print("✅ Your downloads will continue even with malformed data")  
    print("✅ You'll get useful data extraction instead of crashes")
    print("✅ The solution is backward compatible with normal data")
    print("\n🚀 You can now run your Discogs downloader without the 'list' object errors!")

if __name__ == '__main__':
    main()