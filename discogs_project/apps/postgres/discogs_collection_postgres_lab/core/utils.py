"""
Utility functions for the Discogs collection application.
"""

import pandas as pd
import plotly.express as px
from typing import Any, List, Dict
import numpy as np

def is_missing(value) -> bool:
    """
    Safely check if a value is missing/null, handling both scalar and array-like values.
    
    Args:
        value: The value to check
        
    Returns:
        bool: True if the value is missing/null
    """
    if value is None:
        return True
    
    # Handle pandas Series/DataFrame
    if hasattr(value, 'empty'):
        return value.empty
    
    # Handle numpy arrays
    if hasattr(value, '__len__') and hasattr(value, 'dtype'):
        if len(value) == 0:
            return True
        # For arrays, check if all values are null
        try:
            return pd.isna(value).all()
        except (TypeError, ValueError):
            return False
    
    # Handle strings separately (empty string is considered missing)
    if isinstance(value, str):
        return len(value) == 0
    
    # Handle lists and other sequences
    if hasattr(value, '__len__') and not isinstance(value, bytes):
        if len(value) == 0:
            return True
        # For lists, check if all values are None/NaN
        try:
            return all(pd.isna(item) for item in value)
        except (TypeError, ValueError):
            return False
    
    # Handle scalar values
    try:
        return pd.isna(value)
    except (TypeError, ValueError):
        return False

def get_color_map(items: List[str], color_scheme: str) -> Dict[str, str]:
    """
    Generate a color map for items based on the selected color scheme.
    
    Args:
        items: List of items to assign colors to
        color_scheme: Color scheme ('Rainbow', 'Blue', 'Green', 'Red', 'Purple', 'Orange')
        
    Returns:
        Dict mapping items to colors
    """
    if not items:
        return {}
    
    n_items = len(items)
    
    if color_scheme == "Rainbow":
        # Use distinct colors for each item
        colors = px.colors.qualitative.Set3[:n_items] if n_items <= len(px.colors.qualitative.Set3) else px.colors.qualitative.Plotly
        if n_items > len(colors):
            # Cycle through colors if we have more items than colors
            colors = [colors[i % len(colors)] for i in range(n_items)]
    else:
        # Use shades of a single color
        color_maps = {
            "Blue": px.colors.sequential.Blues,
            "Green": px.colors.sequential.Greens,
            "Red": px.colors.sequential.Reds,
            "Purple": px.colors.sequential.Purples,
            "Orange": px.colors.sequential.Oranges
        }
        
        base_colors = color_maps.get(color_scheme, px.colors.sequential.Blues)
        
        if n_items == 1:
            colors = [base_colors[-3]]  # Use a mid-tone for single items
        else:
            # Generate evenly spaced colors from the sequence
            indices = np.linspace(2, len(base_colors) - 1, n_items, dtype=int)
            colors = [base_colors[i] for i in indices]
    
    return dict(zip(items, colors))

def style_with_background(df: pd.DataFrame, subset: list, cmap: str, low: float = 0.3, high: float = 0.9, format_map: dict | None = None):
    """
    Apply background gradient styling to a DataFrame with graceful fallback.
    
    Args:
        df: DataFrame to style
        subset: Columns to apply styling to
        cmap: Colormap name
        low: Low value for color mapping
        high: High value for color mapping
        format_map: Optional formatting map for columns
        
    Returns:
        Styled DataFrame or original DataFrame if styling fails
    """
    try:
        import matplotlib
        styled = df.style.background_gradient(subset=subset, cmap=cmap, low=low, high=high)
        if format_map:
            styled = styled.format(format_map)
        return styled
    except ImportError:
        # Matplotlib not available, return unstyled DataFrame
        if format_map:
            return df.style.format(format_map)
        return df
    except Exception:
        # Any other styling error, return original DataFrame
        return df

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to integer with fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    if is_missing(value):
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float with fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    if is_missing(value):
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def format_large_number(num: int) -> str:
    """
    Format large numbers with appropriate suffixes (K, M, B).
    
    Args:
        num: Number to format
        
    Returns:
        Formatted string
    """
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)

def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def safe_json_loads(json_str: str, default=None):
    """
    Safely parse JSON string with fallback.
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    if is_missing(json_str):
        return default
    
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def format_list_display(items: List[str], max_items: int = 3, separator: str = ", ") -> str:
    """
    Format a list for display with truncation.
    
    Args:
        items: List of items to format
        max_items: Maximum items to show before truncation
        separator: Separator between items
        
    Returns:
        Formatted string
    """
    if not items:
        return ""
    
    if len(items) <= max_items:
        return separator.join(items)
    
    displayed = items[:max_items]
    remaining = len(items) - max_items
    return f"{separator.join(displayed)} (+{remaining} more)"
