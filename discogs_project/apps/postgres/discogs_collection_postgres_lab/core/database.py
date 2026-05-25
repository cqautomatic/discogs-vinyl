"""
Database connection and query management for Discogs collection.
"""

import psycopg2
import psycopg2.extras
import streamlit as st
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class PostgreSQLConfig:
    """Configuration for PostgreSQL connection."""
    host: str = "localhost"
    port: int = 5432
    user: str = "discogs_user"
    password: str = "your_password"
    database: str = "discogs_collection"
    schema: str = "collection_data"

class PostgreSQLConnection:
    """Manages PostgreSQL database connections with proper error handling."""
    
    def __init__(self, config: Optional[PostgreSQLConfig] = None):
        self.config = config or get_postgres_config_from_secrets_env()
        self.connection = None
        self.connect()

    def connect(self):
        """Establish database connection with retry logic."""
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.connection.autocommit = True
            
            # Set search path
            with self.connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {self.config.schema}, public")
                
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            self.connection = None

    def execute_query(self, query: str, params=None):
        """Execute query with proper error handling."""
        if not self.connection:
            st.error("No database connection available")
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:  # SELECT query
                    return cursor.fetchall()
                return []
        except Exception as e:
            st.error(f"Query execution failed: {e}")
            return []

def get_postgres_config_from_secrets_env() -> PostgreSQLConfig:
    """Load PostgreSQL configuration from Streamlit secrets or environment."""
    
    def _to_int(val, default):
        try:
            return int(val) if val else default
        except (ValueError, TypeError):
            return default

    # Try Streamlit secrets first
    if hasattr(st, 'secrets') and 'postgres' in st.secrets:
        postgres_secrets = st.secrets['postgres']
        return PostgreSQLConfig(
            host=postgres_secrets.get('host', 'localhost'),
            port=_to_int(postgres_secrets.get('port'), 5432),
            user=postgres_secrets.get('user', 'discogs_user'),
            password=postgres_secrets.get('password', ''),
            database=postgres_secrets.get('database', 'discogs_collection'),
            schema=postgres_secrets.get('schema', 'collection_data')
        )
    
    # Fallback to environment variables
    return PostgreSQLConfig(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=_to_int(os.getenv('POSTGRES_PORT'), 5432),
        user=os.getenv('POSTGRES_USER', os.getenv('PGUSER', 'discogs_user')),
        password=os.getenv('POSTGRES_PASSWORD', os.getenv('PGPASSWORD', '')),
        database=os.getenv('POSTGRES_DATABASE', os.getenv('PGDATABASE', 'discogs_collection')),
        schema=os.getenv('POSTGRES_SCHEMA', 'collection_data')
    )

@st.cache_resource
def get_database_connection():
    """Get cached database connection."""
    return PostgreSQLConnection()
