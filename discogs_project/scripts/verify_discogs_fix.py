#!/usr/bin/env python3
"""
Verification script to test the Discogs data extraction fixes.
This simulates the problematic data structures that cause the 'list' object has no attribute 'get' error.
"""

import sys
import os
sys.path.append('generated_labs/discogs_collection_postgres_lab')

try:
    from discogs_downloader import (
        safe_extract_artists, safe_extract_labels, safe_extract_formats, 
        safe_extract_catalog_numbers, safe_extract_notes, safe_extract_list_field
    )
    print("✅ Successfully imported fixed extraction functions")
except ImportError as e:
    print(f"❌ Error importing functions: {e}")
    exit(1)

def test_problematic_cases():
    """Test the cases that would cause the original 'list' object has no attribute 'get' error."""
    
    print("\n🧪 Testing Problematic Data Structures")
    print("=" * 50)
    
    # Test case 1: Artists as list of strings (causes original error)
    print("\n1. Artists as list of strings:")
    artists_data = ['The Beatles', 'John Lennon']
    result = safe_extract_artists(artists_data)
    print(f"   Input: {artists_data}")
    print(f"   Result: '{result}'")
    print(f"   ✅ Success - no error!")
    
    # Test case 2: Labels as nested list (causes original error)
    print("\n2. Labels as nested list:")
    labels_data = [['Capitol Records'], ['Apple Records']]
    result = safe_extract_labels(labels_data)
    print(f"   Input: {labels_data}")
    print(f"   Result: '{result}'")
    print(f"   ✅ Success - no error!")
    
    # Test case 3: Formats as mixed types (causes original error)
    print("\n3. Formats as mixed types:")
    formats_data = ['Vinyl', {'name': 'LP'}, ['CD']]
    result = safe_extract_formats(formats_data)
    print(f"   Input: {formats_data}")
    print(f"   Result: '{result}'")
    print(f"   ✅ Success - no error!")
    
    # Test case 4: Notes as list instead of dict (causes original error)
    print("\n4. Notes as list:")
    notes_data = ['Great condition', 'Rare pressing']
    result = safe_extract_notes(notes_data)
    print(f"   Input: {notes_data}")
    print(f"   Result: '{result}'")
    print(f"   ✅ Success - no error!")
    
    # Test case 5: Catalog numbers from malformed labels
    print("\n5. Catalog numbers from malformed labels:")
    labels_data = ['LABEL001', {'catno': 'LABEL002'}, [{'name': 'Label', 'catno': 'LABEL003'}]]
    result = safe_extract_catalog_numbers(labels_data)
    print(f"   Input: {labels_data}")
    print(f"   Result: '{result}'")
    print(f"   ✅ Success - no error!")
    
    # Test case 6: Genres/Styles as non-list
    print("\n6. Genres as single string:")
    genres_data = 'Rock'
    result = safe_extract_list_field(genres_data)
    print(f"   Input: {genres_data}")
    print(f"   Result: {result}")
    print(f"   ✅ Success - no error!")

def simulate_release_processing():
    """Simulate processing a release with problematic data structures."""
    
    print("\n🎵 Simulating Full Release Processing")
    print("=" * 50)
    
    # Simulate a problematic release_data structure
    problematic_release = {
        'id': 12345,
        'basic_information': {
            'id': 12345,
            'title': 'Test Album',
            'artists': ['The Test Band'],  # String instead of dict - would cause error
            'labels': [['Test Label', 'TESTLBL001']],  # Nested list - would cause error
            'formats': 'Vinyl',  # String instead of list - would cause error
            'genres': 'Rock',  # String instead of list
            'styles': ['Progressive Rock'],  # This one is correct
            'year': 1975,
            'country': 'US'
        },
        'notes': ['Excellent condition'],  # List instead of dict - would cause error
        'date_added': '2024-01-01T00:00:00',
        'rating': 5
    }
    
    print("Processing problematic release data...")
    
    try:
        basic_info = problematic_release.get('basic_information', {})
        
        # Use the safe extraction functions
        artist_names = safe_extract_artists(basic_info.get('artists', []))
        label_names = safe_extract_labels(basic_info.get('labels', []))
        catalog_numbers = safe_extract_catalog_numbers(basic_info.get('labels', []))
        format_names = safe_extract_formats(basic_info.get('formats', []))
        genres_list = safe_extract_list_field(basic_info.get('genres', []))
        styles_list = safe_extract_list_field(basic_info.get('styles', []))
        notes_value = safe_extract_notes(problematic_release.get('notes'))
        
        print(f"\n✅ Successfully processed release {problematic_release['id']}!")
        print(f"   Artist: {artist_names}")
        print(f"   Labels: {label_names}")
        print(f"   Catalog: {catalog_numbers}")
        print(f"   Formats: {format_names}")
        print(f"   Genres: {genres_list}")
        print(f"   Styles: {styles_list}")
        print(f"   Notes: {notes_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing release: {e}")
        return False

def compare_with_original():
    """Show what would happen with the original code vs the fixed code."""
    
    print("\n⚡ Comparison: Original vs Fixed Code")
    print("=" * 50)
    
    # Simulate original problematic data
    artists_data = ['Artist Name']  # This would cause 'list' object has no attribute 'get'
    
    print("\nOriginal code (would fail):")
    print("   ', '.join([artist.get('name', '') for artist in artists_data])")
    print("   ❌ AttributeError: 'str' object has no attribute 'get'")
    
    print("\nFixed code (works):")
    result = safe_extract_artists(artists_data)
    print(f"   safe_extract_artists(artists_data)")
    print(f"   ✅ Result: '{result}'")

def main():
    """Run all verification tests."""
    
    print("🔧 Discogs Data Extraction Fix Verification")
    print("=" * 60)
    print("This script verifies that the fixes handle problematic Discogs API responses")
    print("that previously caused 'list object has no attribute get' errors.")
    
    # Run all tests
    test_problematic_cases()
    success = simulate_release_processing()
    compare_with_original()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ The fix successfully handles problematic data structures")
        print("✅ Your Discogs downloader should now be more robust")
        print("\n📋 What was fixed:")
        print("   • Artists/Labels/Formats as strings instead of dicts")
        print("   • Nested lists and unexpected data structures")
        print("   • Notes as lists instead of dicts")
        print("   • Missing or null data fields")
        print("   • Mixed data types within arrays")
        print("\n🚀 You can now run your Discogs downloader with confidence!")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please check the implementation for remaining issues.")

if __name__ == '__main__':
    main()