import os
import sys
import types
import json
import builtins
import pytest
from pathlib import Path
from types import SimpleNamespace

# Create a dummy snowflake.snowpark Session for import-time resolution
snowflake_mod = types.ModuleType('snowflake')
snowflake_snowpark_mod = types.ModuleType('snowflake.snowpark')
snowflake_snowpark_functions_mod = types.ModuleType('snowflake.snowpark.functions')

class DummyBuilder:
    def __init__(self):
        self._configs = None
    def configs(self, cfg):
        self._configs = cfg
        return self
    def create(self):
        return DummySession(self._configs)

class DummySession:
    builder = DummyBuilder()
    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.calls = []
    def use_warehouse(self, wh):
        self.calls.append(('use_warehouse', wh))
    def use_database(self, db):
        self.calls.append(('use_database', db))
    def use_schema(self, sc):
        self.calls.append(('use_schema', sc))
    def sql(self, query):
        self.calls.append(('sql', query))
        class DummyQuery:
            def __init__(self, outer):
                self.outer = outer
                self._bind_kwargs = None
            def bind(self, **kwargs):
                self._bind_kwargs = kwargs
                self.outer.calls.append(('bind', kwargs))
                return self
            def collect(self):
                self.outer.calls.append(('collect', None))
                return []
        return DummyQuery(self)

setattr(snowflake_snowpark_mod, 'Session', DummySession)
sys.modules['snowflake.snowpark.functions'] = snowflake_snowpark_functions_mod
# Provide minimal functions used by importer
setattr(snowflake_snowpark_functions_mod, 'col', lambda *args, **kwargs: None)
setattr(snowflake_snowpark_functions_mod, 'lit', lambda *args, **kwargs: None)
sys.modules['snowflake'] = snowflake_mod
sys.modules['snowflake.snowpark'] = snowflake_snowpark_mod

# Now safe to import module under test (updated path post-reorg)
from discogs_project.apps.snowflake.discogs_collection_snowflake.snowflake_downloader import (
    SnowflakeConfig, get_session, discogs_get, upsert_release
)


def test_snowflake_config_defaults(monkeypatch):
    monkeypatch.delenv('SNOWFLAKE_ACCOUNT', raising=False)
    cfg = SnowflakeConfig()
    assert cfg.role == 'DISCOGS_ADMIN_ROLE'
    assert cfg.database == 'DISCOGS_DB'
    assert cfg.schema == 'COLLECTION_DATA'


def test_to_session_options(monkeypatch):
    monkeypatch.setenv('SNOWFLAKE_ACCOUNT', 'acct')
    monkeypatch.setenv('SNOWFLAKE_USER', 'user')
    monkeypatch.setenv('SNOWFLAKE_PASSWORD', 'pass')
    cfg = SnowflakeConfig()
    opts = cfg.to_session_options()
    assert opts['account'] == 'acct'
    assert opts['user'] == 'user'
    assert opts['password'] == 'pass'
    assert opts['schema'] == 'COLLECTION_DATA'


def test_get_session_uses_builder(monkeypatch):
    cfg = SnowflakeConfig()
    sess = get_session(cfg)
    assert isinstance(sess, DummySession)
    assert sess.cfg['schema'] == 'COLLECTION_DATA'


def test_discogs_get_success(monkeypatch):
    class DummyResp:
        ok = True
        status_code = 200
        text = 'OK'
        def json(self):
            return {'id': 1}
    def fake_get(url, headers=None, timeout=None):
        assert 'Authorization' in headers
        return DummyResp()
    monkeypatch.setenv('DISCOGS_TOKEN', 'T')
    cfg = SnowflakeConfig()
    monkeypatch.setattr('discogs_project.apps.snowflake.discogs_collection_snowflake.snowflake_downloader.requests.get', fake_get)
    data = discogs_get('https://api.discogs.com/releases/1', cfg)
    assert data['id'] == 1


def test_discogs_get_error(monkeypatch):
    class DummyResp:
        ok = False
        status_code = 401
        text = 'Unauthorized'
    def fake_get(url, headers=None, timeout=None):
        return DummyResp()
    cfg = SnowflakeConfig()
    monkeypatch.setattr('discogs_project.apps.snowflake.discogs_collection_snowflake.snowflake_downloader.requests.get', fake_get)
    with pytest.raises(RuntimeError):
        discogs_get('https://api.discogs.com/releases/1', cfg)


def test_upsert_release_builds_merge(monkeypatch):
    sess = DummySession()
    release = {
        'id': 123,
        'title': 'Test Title',
        'artists': [{'name': 'Artist A'}],
        'labels': [{'name': 'Label X'}],
        'year': 1999,
        'country': 'US',
        'genres': ['Rock'],
        'styles': ['Indie'],
        'community': {'have': 10, 'want': 5, 'rating': {'average': 4.5, 'count': 20}}
    }
    upsert_release(sess, release)
    # Verify that SQL and bind calls happened
    assert any(call[0] == 'sql' and 'MERGE INTO DISCOGS_DB.COLLECTION_DATA.RELEASES' in call[1] for call in sess.calls)
    assert any(call[0] == 'bind' for call in sess.calls)
