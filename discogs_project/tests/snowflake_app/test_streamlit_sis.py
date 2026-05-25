import types
import sys
import pytest

# Mock snowflake Session before import
snowflake_mod = types.ModuleType('snowflake')
snowflake_snowpark_mod = types.ModuleType('snowflake.snowpark')
class DummySession:
    def __init__(self):
        pass
    class builder:
        @staticmethod
        def configs(cfg):
            class C:
                def create(self2):
                    return DummySession()
            return C()
    def sql(self, q):
        class Q:
            def to_pandas(self):
                return __import__('pandas').DataFrame()
        return Q()

sys.modules['snowflake'] = snowflake_mod
sys.modules['snowflake.snowpark'] = snowflake_snowpark_mod
setattr(snowflake_snowpark_mod, 'Session', DummySession)

# Ensure streamlit import doesn't run app
import importlib


def test_streamlit_app_imports():
    mod = importlib.import_module('discogs_project.apps.snowflake.discogs_collection_snowflake.streamlit_app_sis')
    assert hasattr(mod, 'get_session')
