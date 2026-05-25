"""
Tests for core.database module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
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

@patch('streamlit.error')
@patch('psycopg2.connect')
def test_database_connection_success(mock_connect, mock_st_error):
    """Test successful database connection establishment."""
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # Properly mock the context manager
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=mock_cursor)
    cursor_context.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = cursor_context
    
    mock_connect.return_value = mock_conn
    
    config = PostgreSQLConfig()
    db = PostgreSQLConnection(config)
    
    assert db.connection == mock_conn
    mock_connect.assert_called_once()
    mock_cursor.execute.assert_called_once_with("SET search_path TO collection_data, public")

@patch('streamlit.error')
@patch('psycopg2.connect')
def test_database_connection_failure(mock_connect, mock_st_error):
    """Test database connection failure handling."""
    mock_connect.side_effect = Exception("Connection failed")
    
    config = PostgreSQLConfig()
    db = PostgreSQLConnection(config)
    
    assert db.connection is None
    mock_st_error.assert_called_once()

@patch('streamlit.error')
def test_query_execution_success(mock_st_error):
    """Test successful query execution with mocked connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # Properly mock the context manager
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=mock_cursor)
    cursor_context.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = cursor_context
    
    mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
    mock_cursor.description = True
    
    config = PostgreSQLConfig()
    db = PostgreSQLConnection.__new__(PostgreSQLConnection)  # Create without calling __init__
    db.connection = mock_conn
    
    result = db.execute_query("SELECT * FROM test")
    
    assert result == [{'id': 1, 'name': 'test'}]
    mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)

@patch('streamlit.error')
def test_query_execution_no_connection(mock_st_error):
    """Test query execution with no connection."""
    config = PostgreSQLConfig()
    db = PostgreSQLConnection.__new__(PostgreSQLConnection)  # Create without calling __init__
    db.connection = None
    
    result = db.execute_query("SELECT * FROM test")
    
    assert result == []
    mock_st_error.assert_called_once_with("No database connection available")

@patch('streamlit.error')
def test_query_execution_failure(mock_st_error):
    """Test query execution failure handling."""
    mock_conn = Mock()
    mock_cursor = Mock()
    
    # Properly mock the context manager
    cursor_context = Mock()
    cursor_context.__enter__ = Mock(return_value=mock_cursor)
    cursor_context.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = cursor_context
    
    mock_cursor.execute.side_effect = Exception("Query failed")
    
    config = PostgreSQLConfig()
    db = PostgreSQLConnection.__new__(PostgreSQLConnection)  # Create without calling __init__
    db.connection = mock_conn
    
    result = db.execute_query("SELECT * FROM test")
    
    assert result == []
    mock_st_error.assert_called_once()
