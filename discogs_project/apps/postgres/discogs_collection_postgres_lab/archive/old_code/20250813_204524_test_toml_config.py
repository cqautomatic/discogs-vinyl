#!/usr/bin/env python3
"""
Test script to verify TOML configuration loading for discogs_downloader.py
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import the config loading function
from discogs_downloader import load_config

def test_toml_loading():
    """Test TOML configuration loading with detailed output."""
    print("🔍 Testing TOML Configuration Loading")
    print("=" * 50)
    
    # Check for TOML library
    try:
        import tomllib as tomli
        print("✅ Using built-in tomllib (Python 3.11+)")
    except ImportError:
        try:
            import tomli
            print("✅ Using tomli library")
        except ImportError:
            print("❌ No TOML library available - install tomli: pip install tomli")
            return False
    
    # Check for secrets.toml file
    candidates = [
        Path('.streamlit/secrets.toml'),
        Path(__file__).resolve().parents[2] / '.streamlit' / 'secrets.toml',
        Path('secrets.toml')
    ]
    
    secrets_file = None
    for candidate in candidates:
        print(f"🔍 Checking: {candidate.absolute()}")
        if candidate.exists():
            secrets_file = candidate
            print(f"✅ Found secrets file: {secrets_file}")
            break
        else:
            print(f"❌ Not found: {candidate}")
    
    if not secrets_file:
        print("\n❌ No secrets.toml file found!")
        print("📝 Create a .streamlit/secrets.toml file with:")
        print("""
[discogs]
token = "YOUR_ACTUAL_DISCOGS_TOKEN"

[postgres]
host = "localhost"
port = 5432
user = "your_username"
password = "your_password"
database = "discogs_collection"
schema = "collection_data"
        """)
        return False
    
    # Try to load and parse the TOML file
    try:
        with open(secrets_file, 'rb') as f:
            secrets = tomli.load(f)
        
        print(f"\n📄 TOML file contents:")
        print(f"Sections found: {list(secrets.keys())}")
        
        if 'discogs' in secrets:
            discogs_section = secrets['discogs']
            print(f"Discogs section keys: {list(discogs_section.keys())}")
            if 'token' in discogs_section:
                token_value = discogs_section['token']
                if token_value and token_value != "YOUR_DISCOGS_TOKEN":
                    print("✅ Discogs token found and looks valid")
                else:
                    print("❌ Discogs token is placeholder - replace 'YOUR_DISCOGS_TOKEN' with actual token")
            else:
                print("❌ No 'token' key in [discogs] section")
        else:
            print("❌ No [discogs] section found in TOML file")
        
        if 'postgres' in secrets:
            postgres_section = secrets['postgres']
            print(f"Postgres section keys: {list(postgres_section.keys())}")
        else:
            print("❌ No [postgres] section found in TOML file")
            
    except Exception as e:
        print(f"❌ Error reading TOML file: {e}")
        return False
    
    # Test the actual config loading
    print(f"\n🔧 Testing load_config() function...")
    try:
        config = load_config()
        if config:
            print("✅ Configuration loaded successfully!")
            print(f"Token present: {'Yes' if config.token else 'No'}")
            print(f"User agent: {config.user_agent}")
            print(f"Database: {config.postgres_database}")
        else:
            print("❌ load_config() returned None - check the logs above")
    except Exception as e:
        print(f"❌ Error in load_config(): {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_toml_loading()
    if success:
        print("\n🎉 TOML configuration test passed!")
    else:
        print("\n💥 TOML configuration test failed!")
    sys.exit(0 if success else 1)
