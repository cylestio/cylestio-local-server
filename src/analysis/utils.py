"""
Utility functions for the analysis layer.

This module provides utility functions for the analysis layer, including
time series formatting, SQL helpers, and token cost calculations.
"""
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func, text
import json


def format_time_series_data(
    data: List[Any], 
    timestamp_field: str = 'timestamp',
    fields: List[Tuple[str, str]] = None,
    time_range: Optional['TimeRange'] = None,
    resolution: Optional['TimeResolution'] = None,
    sort: bool = True
) -> List[Dict[str, Any]]:
    """
    Format time series data for consistent output.
    
    Args:
        data: Raw time series data
        timestamp_field: Name of the timestamp field
        fields: List of (field_name, aggregation_type) tuples
        time_range: Optional time range to fill in missing points
        resolution: Optional time resolution for filling missing points
        sort: Whether to sort by timestamp
        
    Returns:
        Formatted time series data
    """
    from analysis.interface import TimeResolution
    
    # Convert SQL results to dictionaries if needed
    result_dicts = []
    for item in data:
        if hasattr(item, '_asdict'):
            # Handle SQLAlchemy Row objects
            item_dict = item._asdict()
        elif isinstance(item, tuple) and hasattr(item, '_fields'):
            # Handle named tuples
            item_dict = dict(zip(item._fields, item))
        else:
            # Already a dictionary
            item_dict = item
            
        # Ensure timestamps are in ISO format
        if timestamp_field in item_dict and isinstance(item_dict[timestamp_field], datetime):
            item_dict[timestamp_field] = item_dict[timestamp_field].isoformat()
            
        result_dicts.append(item_dict)
    
    # Fill in missing time points if time_range and resolution are provided
    if time_range and resolution and result_dicts:
        filled_data = _fill_missing_time_points(
            result_dicts, 
            timestamp_field, 
            fields or [],
            time_range, 
            resolution
        )
        result_dicts = filled_data
    
    # Sort by timestamp if requested
    if sort and result_dicts and timestamp_field in result_dicts[0]:
        return sorted(result_dicts, key=lambda x: x[timestamp_field])
    
    return result_dicts


def _fill_missing_time_points(
    data: List[Dict[str, Any]],
    timestamp_field: str,
    fields: List[Tuple[str, str]],
    time_range: 'TimeRange',
    resolution: 'TimeResolution'
) -> List[Dict[str, Any]]:
    """
    Fill in missing time points in a time series.
    
    Args:
        data: Time series data
        timestamp_field: Name of the timestamp field
        fields: List of (field_name, aggregation_type) tuples
        time_range: Time range to fill
        resolution: Time resolution
        
    Returns:
        Time series with missing points filled in
    """
    # Convert time resolution to timedelta
    if resolution.value == 'minute':
        delta = timedelta(minutes=1)
    elif resolution.value == 'hour':
        delta = timedelta(hours=1)
    elif resolution.value == 'day':
        delta = timedelta(days=1)
    elif resolution.value == 'week':
        delta = timedelta(weeks=1)
    elif resolution.value == 'month':
        # Approximate month as 30 days
        delta = timedelta(days=30)
    else:
        # Default to day
        delta = timedelta(days=1)
    
    # Create a map of existing points
    point_map = {}
    for point in data:
        if timestamp_field in point:
            # Convert ISO string to datetime if needed
            timestamp = point[timestamp_field]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Format timestamp consistently based on resolution
            if resolution.value == 'minute':
                timestamp = timestamp.replace(second=0, microsecond=0)
            elif resolution.value == 'hour':
                timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
            elif resolution.value == 'day':
                timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            elif resolution.value == 'week':
                # Start of week (Monday)
                timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                timestamp = timestamp - timedelta(days=timestamp.weekday())
            elif resolution.value == 'month':
                timestamp = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
            # Use ISO format as key
            key = timestamp.isoformat()
            point_map[key] = point
    
    # Generate all time points in the range
    start = time_range.start
    end = time_range.end or datetime.utcnow()
    
    # Adjust start and end based on resolution
    if resolution.value == 'minute':
        start = start.replace(second=0, microsecond=0)
        end = end.replace(second=0, microsecond=0)
    elif resolution.value == 'hour':
        start = start.replace(minute=0, second=0, microsecond=0)
        end = end.replace(minute=0, second=0, microsecond=0)
    elif resolution.value == 'day':
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif resolution.value == 'week':
        # Start of week (Monday)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start - timedelta(days=start.weekday())
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end - timedelta(days=end.weekday())
    elif resolution.value == 'month':
        start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    filled_data = []
    current = start
    
    while current <= end:
        key = current.isoformat()
        
        if key in point_map:
            # Use existing point
            filled_data.append(point_map[key])
        else:
            # Create new point with zero values
            new_point = {timestamp_field: key}
            
            # Add fields with zero values or appropriate defaults
            for field_name, agg_type in fields:
                if agg_type in ('sum', 'count', 'avg'):
                    new_point[field_name] = 0
                elif agg_type == 'min':
                    new_point[field_name] = None
                elif agg_type == 'max':
                    new_point[field_name] = None
                else:
                    new_point[field_name] = 0
                    
            filled_data.append(new_point)
        
        # Move to next time point
        current += delta
    
    return filled_data


def sql_time_bucket(timestamp_column, resolution: 'TimeResolution') -> text:
    """
    Generate SQL expression for time bucketing based on resolution.
    
    Args:
        timestamp_column: SQLAlchemy column to bucket
        resolution: Time resolution (minute, hour, day, week, month)
        
    Returns:
        SQLAlchemy text expression for time bucketing
    """
    import sqlalchemy as sa
    from sqlalchemy.dialects import sqlite, mysql, postgresql
    
    resolution_value = resolution.value if hasattr(resolution, 'value') else resolution
    
    # Try to detect SQLite dialect
    dialect_is_sqlite = False
    try:
        from sqlalchemy import inspect
        inspector = inspect(sa.inspect(timestamp_column).table.bind)
        dialect_is_sqlite = isinstance(inspector.dialect, sqlite.dialect.SQLiteDialect)
    except (ImportError, AttributeError, Exception):
        # If we can't determine, check the class name as a fallback
        try:
            dialect_is_sqlite = 'sqlite' in str(timestamp_column.expression.bind.dialect.__class__.__name__).lower()
        except (AttributeError, Exception):
            pass
    
    # For SQLite, use strftime
    if dialect_is_sqlite:
        if resolution_value == 'minute':
            return sa.func.strftime('%Y-%m-%d %H:%M', timestamp_column)
        elif resolution_value == 'hour':
            return sa.func.strftime('%Y-%m-%d %H', timestamp_column)
        elif resolution_value == 'day':
            return sa.func.strftime('%Y-%m-%d', timestamp_column)
        elif resolution_value == 'week':
            # SQLite week handling is different
            return sa.text(f"date({timestamp_column}, '-' || strftime('%w', {timestamp_column}) || ' days', 'weekday 0')")
        elif resolution_value == 'month':
            return sa.func.strftime('%Y-%m', timestamp_column)
        else:
            # Default to day
            return sa.func.strftime('%Y-%m-%d', timestamp_column)
    else:
        # For MySQL/PostgreSQL, use date_format
        if resolution_value == 'minute':
            return sa.func.date_format(timestamp_column, '%Y-%m-%d %H:%i')
        elif resolution_value == 'hour':
            return sa.func.date_format(timestamp_column, '%Y-%m-%d %H')
        elif resolution_value == 'day':
            return sa.func.date_format(timestamp_column, '%Y-%m-%d')
        elif resolution_value == 'week':
            # Using date of the first day of the week
            day_of_week = sa.func.dayofweek(timestamp_column)
            week_start = sa.func.date_sub(timestamp_column, text(f'interval ({day_of_week}-1) day'))
            return sa.func.date_format(week_start, '%Y-%m-%d')
        elif resolution_value == 'month':
            return sa.func.date_format(timestamp_column, '%Y-%m')
        else:
            # Default to day
            return sa.func.date_format(timestamp_column, '%Y-%m-%d')


def calculate_token_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """
    Calculate cost for token usage based on model pricing.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name
        
    Returns:
        Estimated cost in USD
    """
    # Default rates if model is not recognized
    input_rate = 0.0001  # $0.01 per 100 tokens
    output_rate = 0.0002  # $0.02 per 100 tokens
    
    # Define rates for common models
    model_rates = {
        'gpt-3.5-turbo': {'input': 0.0000015, 'output': 0.000002},  # $0.15/0.20 per 100K
        'gpt-4': {'input': 0.00003, 'output': 0.00006},             # $3/6 per 100K
        'gpt-4-turbo': {'input': 0.00001, 'output': 0.00003},       # $1/3 per 100K
        'gpt-4o': {'input': 0.00001, 'output': 0.00003},            # $1/3 per 100K
        'claude-3-opus': {'input': 0.00001, 'output': 0.00003},     # $1/3 per 100K
        'claude-3-sonnet': {'input': 0.000003, 'output': 0.000015}, # $0.3/1.5 per 100K
        'claude-3-haiku': {'input': 0.00000025, 'output': 0.000001} # $0.025/0.1 per 100K
    }
    
    # Check for exact model match
    if model in model_rates:
        input_rate = model_rates[model]['input']
        output_rate = model_rates[model]['output']
    else:
        # Check for partial matches
        for model_name, rates in model_rates.items():
            if model_name in model.lower():
                input_rate = rates['input']
                output_rate = rates['output']
                break
    
    # Calculate cost
    input_cost = input_tokens * input_rate
    output_cost = output_tokens * output_rate
    total_cost = input_cost + output_cost
    
    return total_cost


def deep_get(dictionary: Dict[str, Any], path: str, default=None) -> Any:
    """
    Safely get a value from a nested dictionary using a dotted path.
    
    Args:
        dictionary: The dictionary to search in
        path: The path to the value, using dot notation (e.g., 'a.b.c')
        default: The default value to return if the path doesn't exist
        
    Returns:
        The value at the path, or the default if not found
    """
    if not dictionary or not path:
        return default
    
    keys = path.split('.')
    value = dictionary
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def parse_json_string(json_str: Optional[str], default=None) -> Any:
    """
    Parse a JSON string safely.
    
    Args:
        json_str: JSON string to parse
        default: Default value to return if parsing fails
        
    Returns:
        Parsed JSON object or default if parsing fails
    """
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def extract_keywords(text: str) -> List[str]:
    """
    Extract keywords from text.
    
    This is a simple implementation that extracts words from text.
    In a production environment, this would use NLP techniques for better keyword extraction.
    
    Args:
        text: Text to extract keywords from
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Simple word extraction
    words = text.lower().split()
    
    # Remove common stop words and short words
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
        'when', 'where', 'how', 'who', 'which', 'this', 'that', 'these', 'those',
        'then', 'just', 'so', 'than', 'such', 'both', 'through', 'about', 'for',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'having', 'do', 'does', 'did', 'doing', 'to', 'from', 'in', 'out', 'on',
        'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
        'too', 'very', 'can', 'will', 'with'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    return keywords


def calculate_percentiles(values: List[float], percentiles: List[int] = None) -> Dict[str, float]:
    """
    Calculate percentiles for a list of values.
    
    Args:
        values: List of numeric values
        percentiles: List of percentiles to calculate (default: [50, 75, 90, 95, 99])
        
    Returns:
        Dictionary of percentile name to value
    """
    if not values:
        return {}
    
    if percentiles is None:
        percentiles = [50, 75, 90, 95, 99]
    
    # Sort values for percentile calculation
    sorted_values = sorted(values)
    
    result = {}
    for p in percentiles:
        if p < 0 or p > 100:
            continue  # Skip invalid percentiles
            
        # Calculate index with linear interpolation
        index = (len(sorted_values) - 1) * (p / 100)
        
        if index.is_integer():
            # Exact index
            result[f"p{p}"] = sorted_values[int(index)]
        else:
            # Interpolate between two values
            lower_idx = int(index)
            upper_idx = lower_idx + 1
            
            lower_value = sorted_values[lower_idx]
            upper_value = sorted_values[upper_idx]
            
            # Linear interpolation
            fraction = index - lower_idx
            interpolated = lower_value + (upper_value - lower_value) * fraction
            
            result[f"p{p}"] = interpolated
    
    return result 