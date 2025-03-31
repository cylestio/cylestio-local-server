"""
Tests for utility functions in the analysis layer.
"""
import json
from datetime import datetime
import pytest
from sqlalchemy import Column, String

from analysis.utils import (
    format_time_series_data,
    sql_time_bucket,
    calculate_token_cost,
    parse_json_string,
    extract_keywords
)

from analysis.interface import TimeResolution


def test_format_time_series_data():
    """Test formatting time series data."""
    # Test with datetime objects
    now = datetime.utcnow()
    data = [
        {"timestamp": now, "value": 10},
        {"timestamp": now, "value": 20}
    ]
    
    formatted = format_time_series_data(data)
    
    # Check all timestamps are ISO format strings
    for item in formatted:
        assert isinstance(item["timestamp"], str)
        
    # Test sorting
    data = [
        {"timestamp": "2023-01-03T00:00:00", "value": 30},
        {"timestamp": "2023-01-01T00:00:00", "value": 10},
        {"timestamp": "2023-01-02T00:00:00", "value": 20}
    ]
    
    formatted = format_time_series_data(data)
    assert formatted[0]["timestamp"] == "2023-01-01T00:00:00"
    assert formatted[1]["timestamp"] == "2023-01-02T00:00:00"
    assert formatted[2]["timestamp"] == "2023-01-03T00:00:00"
    
    # Test with no sorting
    formatted = format_time_series_data(data, sort=False)
    assert formatted[0]["timestamp"] == "2023-01-03T00:00:00"


def test_sql_time_bucket():
    """Test SQL time bucket generation."""
    # Create a mock column
    timestamp_column = Column('timestamp', String)
    
    # Test all resolutions
    minute_expr = sql_time_bucket(timestamp_column, TimeResolution('minute'))
    assert 'date_format' in str(minute_expr).lower()
    
    hour_expr = sql_time_bucket(timestamp_column, TimeResolution('hour'))
    assert 'date_format' in str(hour_expr).lower()
    
    day_expr = sql_time_bucket(timestamp_column, TimeResolution('day'))
    assert 'date_format' in str(day_expr).lower()
    
    week_expr = sql_time_bucket(timestamp_column, TimeResolution('week'))
    assert 'date_format' in str(week_expr).lower()
    assert 'date_sub' in str(week_expr).lower() or 'interval' in str(week_expr).lower()
    
    month_expr = sql_time_bucket(timestamp_column, TimeResolution('month'))
    assert 'date_format' in str(month_expr).lower()
    
    # Test fallback with a string (non-TimeResolution) parameter
    default_expr = sql_time_bucket(timestamp_column, 'fallback')
    assert 'date_format' in str(default_expr).lower()
    
    # Test with string resolution of a valid value
    string_expr = sql_time_bucket(timestamp_column, 'day')
    assert 'date_format' in str(string_expr).lower()


def test_calculate_token_cost():
    """Test token cost calculation."""
    # Test known models
    gpt4_cost = calculate_token_cost(1000, 500, "gpt-4")
    assert gpt4_cost > 0
    
    gpt35_cost = calculate_token_cost(1000, 500, "gpt-3.5-turbo")
    assert gpt35_cost > 0
    
    # GPT-4 should be more expensive than GPT-3.5
    assert gpt4_cost > gpt35_cost
    
    # Test claude models
    claude_opus_cost = calculate_token_cost(1000, 500, "claude-3-opus")
    assert claude_opus_cost > 0
    
    claude_sonnet_cost = calculate_token_cost(1000, 500, "claude-3-sonnet")
    assert claude_sonnet_cost > 0
    
    # Opus should be more expensive than Sonnet
    assert claude_opus_cost > claude_sonnet_cost
    
    # Test partial model name matching
    custom_gpt4_cost = calculate_token_cost(1000, 500, "custom-gpt-4-model")
    assert custom_gpt4_cost == gpt4_cost
    
    # Test unknown model (uses default rates)
    unknown_cost = calculate_token_cost(1000, 500, "unknown-model")
    assert unknown_cost > 0


def test_parse_json_string():
    """Test JSON string parsing."""
    # Test valid JSON
    valid_json = '{"key": "value", "number": 42}'
    parsed = parse_json_string(valid_json)
    assert parsed["key"] == "value"
    assert parsed["number"] == 42
    
    # Test invalid JSON
    invalid_json = '{"key": "value", number: 42}'
    parsed = parse_json_string(invalid_json)
    assert parsed is None
    
    # Test None input
    parsed = parse_json_string(None)
    assert parsed is None
    
    # Test empty string
    parsed = parse_json_string("")
    assert parsed is None


def test_extract_keywords():
    """Test keyword extraction from text."""
    # Test normal text
    text = "This is a test sentence with some important keywords like telemetry and analysis"
    keywords = extract_keywords(text)
    assert "test" in keywords
    assert "sentence" in keywords
    assert "important" in keywords
    assert "keywords" in keywords
    assert "telemetry" in keywords
    assert "analysis" in keywords
    
    # Stop words and short words should be filtered out
    assert "this" not in keywords
    assert "is" not in keywords
    assert "a" not in keywords
    assert "with" not in keywords
    assert "some" not in keywords
    
    # Test empty text
    assert extract_keywords("") == []
    assert extract_keywords(None) == [] 