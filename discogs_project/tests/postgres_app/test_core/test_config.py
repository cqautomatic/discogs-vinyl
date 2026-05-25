"""
Tests for core.config module.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from core.config import DiscogsConfig, load_config, validate_config

def test_discogs_config_creation():
    """Test DiscogsConfig creation with default values."""
    config = DiscogsConfig(
        token="test_token",
        user_agent="test_agent",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="test_user",
        postgres_password="test_pass",
        postgres_database="test_db"
    )
    
    assert config.token == "test_token"
    assert config.user_agent == "test_agent"
    assert config.postgres_schema == "collection_data"  # default value
    assert config.local_artwork_path == "./artwork"  # default value
    assert config.rate_limit_delay == 1.0  # default value

@patch('pathlib.Path.exists')
@patch('builtins.open', new_callable=mock_open, read_data=b"""
[discogs]
token = "toml_token"
user_agent = "toml_agent"
username = "toml_user"

[postgres]
host = "toml_host"
port = 5433
user = "toml_pg_user"
password = "toml_pg_pass"
database = "toml_db"
""")
@patch('core.config.TOMLI_AVAILABLE', True)
def test_load_config_from_toml(mock_file, mock_exists):
    """Test loading configuration from secrets.toml."""
    mock_exists.return_value = True
    
    config = load_config()
    
    assert config.token == "toml_token"
    assert config.user_agent == "toml_agent"
    assert config.username == "toml_user"
    assert config.postgres_host == "toml_host"
    assert config.postgres_port == 5433

@patch('core.config.TOMLI_AVAILABLE', False)  # Disable TOML to force JSON loading
@patch('pathlib.Path.exists')
@patch('builtins.open', new_callable=mock_open, read_data='{"discogs_token": "json_token", "user_agent": "json_agent", "postgres_host": "json_host"}')
def test_load_config_from_json(mock_file, mock_exists):
    """Test loading configuration from JSON file."""
    def side_effect(path):
        path_str = str(path)
        if path_str.endswith('secrets.toml'):
            return False
        elif path_str.endswith('discogs_config.json'):
            return True
        return False
    
    # Path.exists is called as a method; accept *args to be safe
    def exists_wrapper(*args, **kwargs):
        return side_effect(args[0]) if args else False
    mock_exists.side_effect = exists_wrapper
    
    config = load_config()
    
    assert config.token == "json_token"
    assert config.user_agent == "json_agent"
    assert config.postgres_host == "json_host"

@patch('pathlib.Path.exists', return_value=False)
@patch.dict(os.environ, {
    'DISCOGS_TOKEN': 'env_token',
    'DISCOGS_USER_AGENT': 'env_agent',
    'POSTGRES_HOST': 'env_host',
    'POSTGRES_PORT': '5434'
})
def test_load_config_from_env(mock_exists):
    """Test loading configuration from environment variables."""
    config = load_config()
    
    assert config.token == "env_token"
    assert config.user_agent == "env_agent"
    assert config.postgres_host == "env_host"
    assert config.postgres_port == 5434

def test_validate_config_valid():
    """Test configuration validation with valid config."""
    config = DiscogsConfig(
        token="valid_token",
        user_agent="test_agent",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="test_user",
        postgres_password="test_pass",
        postgres_database="test_db"
    )
    
    assert validate_config(config) is True

def test_validate_config_missing_token():
    """Test configuration validation with missing token."""
    config = DiscogsConfig(
        token="",  # Empty token
        user_agent="test_agent",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="test_user",
        postgres_password="test_pass",
        postgres_database="test_db"
    )
    
    assert validate_config(config) is False

@patch('core.config.logger')
def test_validate_config_missing_password_warning(mock_logger):
    """Test configuration validation warns about missing password."""
    config = DiscogsConfig(
        token="valid_token",
        user_agent="test_agent",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_user="test_user",
        postgres_password="",  # Empty password
        postgres_database="test_db"
    )
    
    result = validate_config(config)
    
    assert result is True  # Still valid, but should warn
    mock_logger.warning.assert_called_once()
