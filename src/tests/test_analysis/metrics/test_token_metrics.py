"""
Tests for token usage metrics.
"""
import pytest
from datetime import datetime, timedelta

from analysis.metrics import TokenMetrics
from analysis.interface import MetricParams, TimeSeriesParams, TimeResolution, TimeRange


@pytest.fixture
def token_metrics(db_session, mock_data):
    """Create token metrics instance."""
    return TokenMetrics(db_session)


def test_get_token_usage_summary(token_metrics):
    """Test getting token usage summary."""
    # Test without filters
    summary = token_metrics.get_token_usage_summary()
    
    # Verify basic structure
    assert summary is not None
    assert 'total_input_tokens' in summary
    assert 'total_output_tokens' in summary
    assert 'total_tokens' in summary
    assert 'avg_input_tokens' in summary
    assert 'avg_output_tokens' in summary
    assert 'avg_tokens' in summary
    assert 'interaction_count' in summary
    assert 'estimated_cost' in summary
    assert 'model_breakdown' in summary
    
    # Verify values make sense
    assert summary['total_input_tokens'] > 0
    assert summary['total_output_tokens'] > 0
    assert summary['total_tokens'] > 0
    assert summary['interaction_count'] > 0
    assert summary['estimated_cost'] > 0
    assert len(summary['model_breakdown']) > 0
    
    # Test with filter by agent
    params = MetricParams(agent_ids=["agent-0"])
    filtered_summary = token_metrics.get_token_usage_summary(params)
    
    # Filtered summary should have fewer interactions
    assert filtered_summary['interaction_count'] < summary['interaction_count']
    
    # Test with time range filter
    time_range = TimeRange(
        start=datetime.utcnow() - timedelta(hours=1),
        end=datetime.utcnow()
    )
    params = MetricParams(time_range=time_range)
    time_filtered_summary = token_metrics.get_token_usage_summary(params)
    
    # Time filtered summary might have fewer interactions
    assert time_filtered_summary['interaction_count'] <= summary['interaction_count']


def test_get_token_usage_by_agent(token_metrics):
    """Test getting token usage by agent."""
    # Test without filters
    result = token_metrics.get_token_usage_by_agent()
    
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
        assert 'agent_id' in item
        assert 'input_tokens' in item
        assert 'output_tokens' in item
        assert 'total_tokens' in item
        assert 'interaction_count' in item
        assert 'estimated_cost' in item
        
        # Values should be valid
        assert item['input_tokens'] > 0
        assert item['output_tokens'] > 0
        assert item['total_tokens'] > 0
        assert item['interaction_count'] > 0
        assert item['estimated_cost'] > 0


def test_get_token_usage_by_model(token_metrics):
    """Test getting token usage by model."""
    # Test without filters
    result = token_metrics.get_token_usage_by_model()
    
    # Verify structure
    assert result is not None
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')
    
    # Verify content
    assert len(result.items) > 0
    for item in result.items:
        assert 'model' in item
        assert 'vendor' in item
        assert 'input_tokens' in item
        assert 'output_tokens' in item
        assert 'total_tokens' in item
        assert 'interaction_count' in item
        assert 'estimated_cost' in item
        
        # Values should be valid
        assert item['input_tokens'] > 0
        assert item['output_tokens'] > 0
        assert item['total_tokens'] > 0
        assert item['interaction_count'] > 0
        assert item['estimated_cost'] > 0


def test_get_token_usage_time_series(token_metrics):
    """Test getting token usage time series."""
    # Test with hourly resolution
    params = TimeSeriesParams(resolution=TimeResolution.HOUR)
    time_series = token_metrics.get_token_usage_time_series(params)
    
    # Verify structure
    assert isinstance(time_series, list)
    
    # May be empty if all events are in same hour
    if time_series:
        for point in time_series:
            assert 'timestamp' in point
            assert 'input_tokens' in point
            assert 'output_tokens' in point
            assert 'total_tokens' in point
            assert 'interaction_count' in point
    
    # Test with daily resolution
    params = TimeSeriesParams(resolution=TimeResolution.DAY)
    time_series = token_metrics.get_token_usage_time_series(params)
    
    if time_series:
        # Timestamp should be in ISO format
        for point in time_series:
            # Should be date format YYYY-MM-DD with optional time
            assert len(point['timestamp']) >= 10


def test_get_token_usage_percentiles(token_metrics):
    """Test getting token usage percentiles."""
    # Test without filters
    percentiles = token_metrics.get_token_usage_percentiles()
    
    # Verify structure
    assert percentiles is not None
    assert 'input_tokens' in percentiles
    assert 'output_tokens' in percentiles
    assert 'total_tokens' in percentiles
    
    # Check percentile values
    for metric in ['input_tokens', 'output_tokens', 'total_tokens']:
        assert 'p50' in percentiles[metric]
        assert 'p75' in percentiles[metric]
        assert 'p90' in percentiles[metric]
        assert 'p95' in percentiles[metric]
        assert 'p99' in percentiles[metric]
        
        # Values should be in ascending order
        assert percentiles[metric]['p50'] <= percentiles[metric]['p75']
        assert percentiles[metric]['p75'] <= percentiles[metric]['p90']
        assert percentiles[metric]['p90'] <= percentiles[metric]['p95']
        assert percentiles[metric]['p95'] <= percentiles[metric]['p99'] 