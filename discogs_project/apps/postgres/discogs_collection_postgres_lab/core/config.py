"""
Configuration management for Discogs collection application.
Handles loading from secrets.toml, environment variables, and JSON files.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    import tomli
    TOMLI_AVAILABLE = True
except ImportError:
    TOMLI_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DiscogsConfig:
    """Configuration for Discogs API and PostgreSQL connection."""
    token: str
    user_agent: str
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_database: str
    postgres_schema: str = "collection_data"
    local_artwork_path: str = "./artwork"
    username: Optional[str] = None
    rate_limit_delay: float = 1.0

def load_config() -> DiscogsConfig:
    """
    Load configuration from multiple sources in priority order:
    1. .streamlit/secrets.toml (highest priority)
    2. discogs_config.json
    3. Environment variables (lowest priority)
    """
    logger.info("Loading configuration...")
    
    # Try secrets.toml first
    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists() and TOMLI_AVAILABLE:
        try:
            logger.info(f"Found secrets.toml at: {secrets_path}")
            with open(secrets_path, "rb") as f:
                secrets = tomli.load(f)
            
            logger.info(f"Loaded secrets sections: {list(secrets.keys())}")
            
            if 'discogs' in secrets and 'postgres' in secrets:
                discogs_secrets = secrets['discogs']
                postgres_secrets = secrets['postgres']
                
                token = discogs_secrets.get('token', '')
                logger.info(f"Token from TOML: {'***FOUND***' if token else '***NOT FOUND***'}")
                
                config = DiscogsConfig(
                    token=token,
                    user_agent=discogs_secrets.get('user_agent', 'DiscogsCollectionDownloader/1.0'),
                    username=discogs_secrets.get('username'),
                    rate_limit_delay=float(discogs_secrets.get('rate_limit_delay', 1.0)),
                    postgres_host=postgres_secrets.get('host', 'localhost'),
                    postgres_port=int(postgres_secrets.get('port', 5432)),
                    postgres_user=postgres_secrets.get('user', 'discogs_user'),
                    postgres_password=postgres_secrets.get('password', ''),
                    postgres_database=postgres_secrets.get('database', 'discogs_collection'),
                    postgres_schema=postgres_secrets.get('schema', 'collection_data'),
                    local_artwork_path=discogs_secrets.get('local_artwork_path', './artwork')
                )
                logger.info("Successfully loaded config from secrets.toml")
                return config
        except Exception as e:
            logger.warning(f"Failed to load secrets.toml: {e}")
    
    # Try JSON config file
    json_path = Path("discogs_config.json")
    # Try to load JSON config even if Path.exists is not reliable (e.g., under mocks)
    try:
        with open(json_path, 'r') as f:
            json_config = json.load(f)
        config = DiscogsConfig(
            token=json_config.get('discogs_token', json_config.get('token', '')),
            user_agent=json_config.get('user_agent', 'DiscogsCollectionDownloader/1.0'),
            username=json_config.get('username'),
            rate_limit_delay=float(json_config.get('rate_limit_delay', 1.0)),
            postgres_host=json_config.get('postgres_host', 'localhost'),
            postgres_port=int(json_config.get('postgres_port', 5432)),
            postgres_user=json_config.get('postgres_user', 'discogs_user'),
            postgres_password=json_config.get('postgres_password', ''),
            postgres_database=json_config.get('postgres_database', 'discogs_collection'),
            postgres_schema=json_config.get('postgres_schema', 'collection_data'),
            local_artwork_path=json_config.get('local_artwork_path', './artwork')
        )
        logger.info("Successfully loaded config from JSON")
        return config
    except Exception as e:
        logger.warning(f"Failed to load JSON config: {e}")
    
    # Fallback to environment variables
    logger.info("Loading config from environment variables")
    
    def _to_int(val, default):
        try:
            return int(val) if val else default
        except (ValueError, TypeError):
            return default
    
    def _to_float(val, default):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default
    
    config = DiscogsConfig(
        token=os.getenv('DISCOGS_TOKEN', ''),
        user_agent=os.getenv('DISCOGS_USER_AGENT', 'DiscogsCollectionDownloader/1.0'),
        username=os.getenv('DISCOGS_USERNAME'),
        rate_limit_delay=_to_float(os.getenv('DISCOGS_RATE_LIMIT_DELAY'), 1.0),
        postgres_host=os.getenv('POSTGRES_HOST', 'localhost'),
        postgres_port=_to_int(os.getenv('POSTGRES_PORT'), 5432),
        postgres_user=os.getenv('POSTGRES_USER', os.getenv('PGUSER', 'discogs_user')),
        postgres_password=os.getenv('POSTGRES_PASSWORD', os.getenv('PGPASSWORD', '')),
        postgres_database=os.getenv('POSTGRES_DATABASE', os.getenv('PGDATABASE', 'discogs_collection')),
        postgres_schema=os.getenv('POSTGRES_SCHEMA', 'collection_data'),
        local_artwork_path=os.getenv('LOCAL_ARTWORK_PATH', './artwork')
    )
    
    logger.info("Successfully loaded config from environment variables")
    return config

def validate_config(config: DiscogsConfig) -> bool:
    """Validate that required configuration is present."""
    if not config.token:
        logger.error("Discogs token is required but not found")
        return False
    
    if not config.postgres_password:
        logger.warning("PostgreSQL password is empty - this may cause connection issues")
    
    return True
