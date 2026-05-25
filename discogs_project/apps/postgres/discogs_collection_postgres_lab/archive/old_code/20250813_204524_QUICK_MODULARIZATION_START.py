#!/usr/bin/env python3
"""
Quick start script to begin modularization of streamlit_app.py

This script demonstrates how to extract the first module (core/database.py)
as an example of the modularization process.
"""

import os
from pathlib import Path

def create_directory_structure():
    """Create the modular directory structure."""
    directories = [
        'core',
        'data', 
        'components',
        'views',
        'tests/test_core',
        'tests/test_data',
        'tests/test_components', 
        'tests/test_views'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Create __init__.py files
        init_file = Path(directory) / '__init__.py'
        if not init_file.exists():
            init_file.write_text('"""Module initialization."""\n')
    
    print("✓ Directory structure created")

def extract_database_module():
    """Extract database-related code to core/database.py"""
    
    database_code = '''"""
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
'''
    
    # Write the database module
    with open('core/database.py', 'w') as f:
        f.write(database_code)
    
    print("✓ core/database.py created")

def create_example_test():
    """Create an example test file."""
    
    test_code = '''"""
Tests for core.database module.
"""

import pytest
from unittest.mock import Mock, patch
from core.database import PostgreSQLConnection, PostgreSQLConfig

def test_postgres_config_creation():
    """Test PostgreSQL configuration creation."""
    config = PostgreSQLConfig(
        host="test_host",
        port=5433,
        user="test_user",
        password="test_pass",
        database="test_db"
    )
    
    assert config.host == "test_host"
    assert config.port == 5433
    assert config.user == "test_user"

@patch('psycopg2.connect')
def test_database_connection(mock_connect):
    """Test database connection establishment."""
    mock_conn = Mock()
    mock_connect.return_value = mock_conn
    
    config = PostgreSQLConfig()
    db = PostgreSQLConnection(config)
    
    assert db.connection == mock_conn
    mock_connect.assert_called_once()

def test_query_execution():
    """Test query execution with mocked connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
    mock_cursor.description = True
    
    db = PostgreSQLConnection()
    db.connection = mock_conn
    
    result = db.execute_query("SELECT * FROM test")
    
    assert result == [{'id': 1, 'name': 'test'}]
    mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)
'''
    
    with open('tests/test_core/test_database.py', 'w') as f:
        f.write(test_code)
    
    print("✓ tests/test_core/test_database.py created")

def create_requirements_test():
    """Create requirements-test.txt for testing dependencies."""
    
    test_requirements = '''# Testing dependencies
pytest>=7.0.0
pytest-mock>=3.10.0
pytest-cov>=4.0.0
'''
    
    with open('requirements-test.txt', 'w') as f:
        f.write(test_requirements)
    
    print("✓ requirements-test.txt created")

def main():
    """Run the quick modularization start."""
    print("🚀 Starting modularization of streamlit_app.py...")
    print()
    
    create_directory_structure()
    extract_database_module()
    create_example_test()
    create_requirements_test()
    
    print()
    print("✅ Quick modularization start complete!")
    print()
    print("Next steps:")
    print("1. Install test dependencies: pip install -r requirements-test.txt")
    print("2. Run tests: pytest tests/")
    print("3. Update streamlit_app.py to import from core.database")
    print("4. Continue with Phase 2: Extract data layer")
    print()
    print("See MODULARIZATION_PLAN.md for complete roadmap.")

if __name__ == "__main__":
    main()
