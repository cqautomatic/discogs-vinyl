"""
Tests for core.utils module.
"""

import pytest
import pandas as pd
import numpy as np
from core.utils import (
    is_missing, get_color_map, safe_int_conversion, safe_float_conversion,
    format_large_number, truncate_text, safe_json_loads, format_list_display
)

class TestIsMissing:
    """Tests for is_missing function."""
    
    def test_none_value(self):
        assert is_missing(None) is True
    
    def test_empty_list(self):
        assert is_missing([]) is True
    
    def test_non_empty_list(self):
        assert is_missing([1, 2, 3]) is False
    
    def test_empty_string(self):
        assert is_missing("") is True
    
    def test_non_empty_string(self):
        assert is_missing("test") is False
    
    def test_nan_value(self):
        assert is_missing(np.nan) is True
    
    def test_numeric_value(self):
        assert is_missing(42) is False
    
    def test_pandas_series_empty(self):
        series = pd.Series([], dtype=object)
        assert is_missing(series) is True
    
    def test_pandas_series_with_data(self):
        series = pd.Series([1, 2, 3])
        assert is_missing(series) is False

class TestGetColorMap:
    """Tests for get_color_map function."""
    
    def test_empty_items(self):
        result = get_color_map([], "Rainbow")
        assert result == {}
    
    def test_rainbow_scheme(self):
        items = ["item1", "item2", "item3"]
        result = get_color_map(items, "Rainbow")
        
        assert len(result) == 3
        assert "item1" in result
        assert "item2" in result
        assert "item3" in result
    
    def test_blue_scheme(self):
        items = ["item1", "item2"]
        result = get_color_map(items, "Blue")
        
        assert len(result) == 2
        assert all(isinstance(color, str) for color in result.values())
    
    def test_single_item_blue_scheme(self):
        items = ["single_item"]
        result = get_color_map(items, "Blue")
        
        assert len(result) == 1
        assert "single_item" in result

class TestSafeConversions:
    """Tests for safe conversion functions."""
    
    def test_safe_int_conversion_valid(self):
        assert safe_int_conversion("42") == 42
        assert safe_int_conversion(42.7) == 42
        assert safe_int_conversion(42) == 42
    
    def test_safe_int_conversion_invalid(self):
        assert safe_int_conversion("invalid") == 0
        assert safe_int_conversion(None) == 0
        assert safe_int_conversion("") == 0
    
    def test_safe_int_conversion_custom_default(self):
        assert safe_int_conversion("invalid", -1) == -1
    
    def test_safe_float_conversion_valid(self):
        assert safe_float_conversion("42.5") == 42.5
        assert safe_float_conversion(42) == 42.0
        assert safe_float_conversion(42.7) == 42.7
    
    def test_safe_float_conversion_invalid(self):
        assert safe_float_conversion("invalid") == 0.0
        assert safe_float_conversion(None) == 0.0
        assert safe_float_conversion("") == 0.0
    
    def test_safe_float_conversion_custom_default(self):
        assert safe_float_conversion("invalid", -1.0) == -1.0

class TestFormatting:
    """Tests for formatting functions."""
    
    def test_format_large_number_billions(self):
        assert format_large_number(1_500_000_000) == "1.5B"
    
    def test_format_large_number_millions(self):
        assert format_large_number(2_500_000) == "2.5M"
    
    def test_format_large_number_thousands(self):
        assert format_large_number(1_500) == "1.5K"
    
    def test_format_large_number_small(self):
        assert format_large_number(500) == "500"
    
    def test_truncate_text_short(self):
        text = "Short text"
        assert truncate_text(text, 50) == "Short text"
    
    def test_truncate_text_long(self):
        text = "This is a very long text that should be truncated"
        result = truncate_text(text, 20)
        assert len(result) == 20
        assert result.endswith("...")
    
    def test_truncate_text_empty(self):
        assert truncate_text("", 10) == ""
        assert truncate_text(None, 10) is None

class TestJSONAndListFormatting:
    """Tests for JSON and list formatting functions."""
    
    def test_safe_json_loads_valid(self):
        json_str = '{"key": "value"}'
        result = safe_json_loads(json_str)
        assert result == {"key": "value"}
    
    def test_safe_json_loads_invalid(self):
        json_str = '{"invalid": json}'
        result = safe_json_loads(json_str, {"default": "value"})
        assert result == {"default": "value"}
    
    def test_safe_json_loads_none(self):
        result = safe_json_loads(None, "default")
        assert result == "default"
    
    def test_format_list_display_short(self):
        items = ["item1", "item2"]
        result = format_list_display(items, 3)
        assert result == "item1, item2"
    
    def test_format_list_display_long(self):
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = format_list_display(items, 3)
        assert result == "item1, item2, item3 (+2 more)"
    
    def test_format_list_display_empty(self):
        result = format_list_display([])
        assert result == ""
    
    def test_format_list_display_custom_separator(self):
        items = ["item1", "item2", "item3"]
        result = format_list_display(items, 5, " | ")
        assert result == "item1 | item2 | item3"
