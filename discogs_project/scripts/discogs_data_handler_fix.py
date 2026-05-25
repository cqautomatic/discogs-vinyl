#!/usr/bin/env python3
"""
Robust data handler for Discogs API responses that handles unexpected data structures.
This fixes the "list object has no attribute 'get'" error.
"""

import logging

logger = logging.getLogger(__name__)

def safe_get_name(item, field_name='name', default=''):
    """
    Safely extract a name field from an item that might be a dict, list, or string.
    
    Args:
        item: The item to extract from (dict, list, string, or other)
        field_name: The field to extract (default: 'name')
        default: Default value if extraction fails
    
    Returns:
        Extracted value or default
    """
    try:
        if isinstance(item, dict):
            return item.get(field_name, default)
        elif isinstance(item, str):
            return item
        elif isinstance(item, list):
            # Sometimes Discogs returns nested lists
            if len(item) > 0 and isinstance(item[0], dict):
                return item[0].get(field_name, default)
            elif len(item) > 0 and isinstance(item[0], str):
                return item[0]
            else:
                return default
        elif item is None:
            return default
        else:
            # Try to convert to string as fallback
            return str(item)
    except Exception as e:
        logger.debug(f"Error extracting {field_name} from {type(item)}: {e}")
        return default

def safe_get_catno(item, default=''):
    """
    Safely extract catalog number from a label item.
    
    Args:
        item: The label item to extract from
        default: Default value if extraction fails
    
    Returns:
        Catalog number or default
    """
    return safe_get_name(item, 'catno', default)

def safe_extract_artists(artists_data):
    """
    Safely extract artist names from artists data.
    
    Args:
        artists_data: The artists data from Discogs API
        
    Returns:
        Comma-separated string of artist names
    """
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
    """
    Safely extract label names from labels data.
    
    Args:
        labels_data: The labels data from Discogs API
        
    Returns:
        Comma-separated string of label names
    """
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
    """
    Safely extract catalog numbers from labels data.
    
    Args:
        labels_data: The labels data from Discogs API
        
    Returns:
        Comma-separated string of catalog numbers
    """
    if not labels_data:
        return ''
    
    try:
        if isinstance(labels_data, list):
            catnos = []
            for label in labels_data:
                catno = safe_get_catno(label, '')
                if catno:
                    catnos.append(catno)
            return ', '.join(catnos)
        elif isinstance(labels_data, dict):
            return safe_get_catno(labels_data, '')
        elif isinstance(labels_data, str):
            return labels_data
        else:
            return ''
    except Exception as e:
        logger.warning(f"Error extracting catalog numbers: {e}")
        return ''

def safe_extract_formats(formats_data):
    """
    Safely extract format names from formats data.
    
    Args:
        formats_data: The formats data from Discogs API
        
    Returns:
        Comma-separated string of format names
    """
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

def safe_extract_list_field(data, default=None):
    """
    Safely extract a field that should be a list.
    
    Args:
        data: The data to extract from
        default: Default value if extraction fails (defaults to empty list)
        
    Returns:
        List or default value
    """
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

def safe_extract_notes(notes_data):
    """
    Safely extract notes value from notes data.
    
    Args:
        notes_data: The notes data from Discogs API
        
    Returns:
        Notes string or None
    """
    if not notes_data:
        return None
    
    try:
        if isinstance(notes_data, dict):
            return notes_data.get('value', None)
        elif isinstance(notes_data, str):
            return notes_data
        elif isinstance(notes_data, list):
            # Sometimes notes come as a list
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

def validate_and_log_data_structure(release_data, release_id):
    """
    Validate and log unexpected data structures for debugging.
    
    Args:
        release_data: The release data from Discogs API
        release_id: Release ID for logging
    """
    try:
        basic_info = release_data.get('basic_information', {})
        
        # Check artists structure
        artists = basic_info.get('artists', [])
        if artists and not isinstance(artists, list):
            logger.warning(f"Release {release_id}: Expected artists to be list, got {type(artists)}")
        elif isinstance(artists, list):
            for i, artist in enumerate(artists):
                if not isinstance(artist, dict):
                    logger.warning(f"Release {release_id}: Expected artist {i} to be dict, got {type(artist)}: {artist}")
        
        # Check labels structure
        labels = basic_info.get('labels', [])
        if labels and not isinstance(labels, list):
            logger.warning(f"Release {release_id}: Expected labels to be list, got {type(labels)}")
        elif isinstance(labels, list):
            for i, label in enumerate(labels):
                if not isinstance(label, dict):
                    logger.warning(f"Release {release_id}: Expected label {i} to be dict, got {type(label)}: {label}")
        
        # Check formats structure
        formats = basic_info.get('formats', [])
        if formats and not isinstance(formats, list):
            logger.warning(f"Release {release_id}: Expected formats to be list, got {type(formats)}")
        elif isinstance(formats, list):
            for i, fmt in enumerate(formats):
                if not isinstance(fmt, dict):
                    logger.warning(f"Release {release_id}: Expected format {i} to be dict, got {type(fmt)}: {fmt}")
        
        # Check notes structure
        notes = release_data.get('notes')
        if notes and not isinstance(notes, (dict, str, type(None))):
            logger.warning(f"Release {release_id}: Expected notes to be dict/str/None, got {type(notes)}: {notes}")
            
    except Exception as e:
        logger.error(f"Error validating data structure for release {release_id}: {e}")

# Test function to demonstrate the fixes
def test_safe_extraction():
    """Test the safe extraction functions with various data types."""
    
    test_cases = [
        # Normal case - list of dicts
        {'artists': [{'name': 'Artist 1'}, {'name': 'Artist 2'}]},
        
        # Edge case - list of strings
        {'artists': ['Artist 1', 'Artist 2']},
        
        # Edge case - single dict
        {'artists': {'name': 'Single Artist'}},
        
        # Edge case - single string
        {'artists': 'Single Artist'},
        
        # Edge case - nested list
        {'artists': [['Artist 1'], ['Artist 2']]},
        
        # Edge case - empty/None
        {'artists': []},
        {'artists': None},
        
        # Edge case - unexpected type
        {'artists': 12345},
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"Test case {i + 1}: {test_case}")
        result = safe_extract_artists(test_case.get('artists'))
        print(f"Result: '{result}'")
        print()

if __name__ == '__main__':
    test_safe_extraction()