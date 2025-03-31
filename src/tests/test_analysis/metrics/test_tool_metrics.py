"""
Tests for tool usage metrics.
"""
import pytest
from datetime import datetime, timedelta

from analysis.metrics import ToolMetrics
from analysis.interface import MetricParams, TimeSeriesParams, TimeResolution, TimeRange


@pytest.fixture
def tool_metrics(db_session, mock_data):
    """Create tool metrics instance."""
    return ToolMetrics(db_session)


def test_get_tool_usage_summary(tool_metrics):
    """Test getting tool usage summary."""
    # Test without filters
    summary = tool_metrics.get_tool_usage_summary()
    
    # Verify basic structure
    assert summary is not None
    assert 'total_tool_calls' in summary
    assert 'unique_tools' in summary
    assert 'successful_calls' in summary
    assert 'failed_calls' in summary
    assert 'success_rate' in summary
    assert 'agents_using_tools' in summary
    
    # Verify values make sense
    assert summary['total_tool_calls'] > 0
    assert summary['unique_tools'] > 0
    assert summary['success_rate'] >= 0
    assert summary['success_rate'] <= 100
    assert summary['successful_calls'] + summary['failed_calls'] == summary['total_tool_calls']
    assert summary['agents_using_tools'] > 0
    
    # Test with filter by agent
    params = MetricParams(agent_ids=["agent-0"])
    filtered_summary = tool_metrics.get_tool_usage_summary(params)
    
    # Filtered summary should have fewer calls
    assert filtered_summary['total_tool_calls'] < summary['total_tool_calls']
    
    # Test with time range filter
    time_range = TimeRange(
        start=datetime.utcnow() - timedelta(hours=1),
        end=datetime.utcnow()
    )
    params = MetricParams(time_range=time_range)
    time_filtered_summary = tool_metrics.get_tool_usage_summary(params)
    
    # Time filtered summary might have fewer calls
    assert time_filtered_summary['total_tool_calls'] <= summary['total_tool_calls']


def test_get_tool_usage_by_name(tool_metrics):
    """Test getting tool usage by tool name."""
    # Test without filters
    result = tool_metrics.get_tool_usage_by_name()
    
    # Verify structure
    assert result is not None
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')
    assert hasattr(result, 'page')
    assert hasattr(result, 'page_size')
    assert hasattr(result, 'total_pages')
    
    # Verify content
    assert len(result.items) > 0
    for item in result.items:
        assert 'tool_name' in item
        assert 'call_count' in item
        assert 'successful_calls' in item
        assert 'failed_calls' in item
        assert 'success_rate' in item
        assert 'agent_count' in item
        
        # Values should be valid
        assert item['call_count'] > 0
        assert item['success_rate'] >= 0
        assert item['success_rate'] <= 100
        assert item['successful_calls'] + item['failed_calls'] == item['call_count']
        assert item['agent_count'] > 0


def test_get_tool_usage_by_agent(tool_metrics):
    """Test getting tool usage by agent."""
    # Test without filters
    result = tool_metrics.get_tool_usage_by_agent()
    
    # Verify structure
    assert result is not None
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')
    
    # Verify content
    assert len(result.items) > 0
    for item in result.items:
        assert 'agent_id' in item
        assert 'call_count' in item
        assert 'unique_tools' in item
        assert 'successful_calls' in item
        assert 'failed_calls' in item
        assert 'success_rate' in item
        
        # Values should be valid
        assert item['call_count'] > 0
        assert item['unique_tools'] > 0
        assert item['success_rate'] >= 0
        assert item['success_rate'] <= 100
        assert item['successful_calls'] + item['failed_calls'] == item['call_count']


def test_get_tool_usage_time_series(tool_metrics):
    """Test getting tool usage time series."""
    # Test with hourly resolution
    params = TimeSeriesParams(resolution=TimeResolution.HOUR)
    time_series = tool_metrics.get_tool_usage_time_series(params)
    
    # Verify structure
    assert isinstance(time_series, list)
    
    # May be empty if all events are in same hour
    if time_series:
        for point in time_series:
            assert 'timestamp' in point
            assert 'call_count' in point
            assert 'successful_calls' in point
            assert 'failed_calls' in point
            assert 'success_rate' in point
            
            # Values should be valid
            assert point['success_rate'] >= 0
            assert point['success_rate'] <= 100
            assert point['successful_calls'] + point['failed_calls'] == point['call_count']
    
    # Test with daily resolution
    params = TimeSeriesParams(resolution=TimeResolution.DAY)
    time_series = tool_metrics.get_tool_usage_time_series(params)
    
    if time_series:
        # Timestamp should be in ISO format
        for point in time_series:
            # Should be date format YYYY-MM-DD with optional time
            assert len(point['timestamp']) >= 10


def test_get_tool_performance_metrics(tool_metrics):
    """Test getting tool performance metrics."""
    # Test without filters
    performance = tool_metrics.get_tool_performance_metrics()
    
    # Verify structure
    assert performance is not None
    assert 'overall' in performance
    assert 'by_tool' in performance
    
    # Check overall metrics
    assert 'avg_duration_ms' in performance['overall']
    assert 'min_duration_ms' in performance['overall']
    assert 'max_duration_ms' in performance['overall']
    assert 'call_count' in performance['overall']
    
    # Verify values make sense
    assert performance['overall']['min_duration_ms'] <= performance['overall']['avg_duration_ms']
    assert performance['overall']['avg_duration_ms'] <= performance['overall']['max_duration_ms']
    
    # Check tool-specific metrics
    assert isinstance(performance['by_tool'], list)
    if performance['by_tool']:
        for tool in performance['by_tool']:
            assert 'tool_name' in tool
            assert 'avg_duration_ms' in tool
            assert 'min_duration_ms' in tool
            assert 'max_duration_ms' in tool
            assert 'call_count' in tool
            
            # Values should be valid
            assert tool['min_duration_ms'] <= tool['avg_duration_ms']
            assert tool['avg_duration_ms'] <= tool['max_duration_ms']


def test_get_error_analysis(tool_metrics):
    """Test getting tool error analysis."""
    # Test without filters
    errors = tool_metrics.get_error_analysis()
    
    # Verify structure
    assert errors is not None
    assert 'error_count' in errors
    assert 'by_tool' in errors
    
    # Error count should be non-negative
    assert errors['error_count'] >= 0
    
    # Check tool errors
    assert isinstance(errors['by_tool'], list)
    if errors['by_tool']:
        for tool in errors['by_tool']:
            assert 'tool_name' in tool
            assert 'error_count' in tool
            assert 'total_count' in tool
            assert 'error_percentage' in tool
            
            # Values should be valid
            assert tool['error_count'] > 0
            assert tool['error_percentage'] >= 0
            assert tool['error_percentage'] <= 100 