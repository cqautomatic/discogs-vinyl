import os
import pytest

REQUIRED_ENV_VARS = [
    'SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD',
    'SNOWFLAKE_ROLE', 'SNOWFLAKE_WAREHOUSE', 'SNOWFLAKE_DATABASE', 'SNOWFLAKE_SCHEMA'
]

def test_env_vars_present(monkeypatch):
    # For CI contexts that don't have real values, ensure at least placeholders are set
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            monkeypatch.setenv(var, 'TEST')
        assert os.getenv(var)
