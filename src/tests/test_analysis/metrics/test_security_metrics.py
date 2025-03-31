"""
Tests for security metrics.
"""
import pytest
from datetime import datetime, timedelta

from analysis.metrics import SecurityMetrics
from analysis.interface import MetricParams, TimeSeriesParams, TimeResolution, TimeRange


@pytest.fixture
def security_metrics(db_session, mock_data):
    """Create security metrics instance."""
    return SecurityMetrics(db_session)


def test_get_security_alerts_summary(security_metrics):
    """Test getting security alerts summary."""
    # Test without filters
    summary = security_metrics.get_security_alerts_summary()
    
    # Verify basic structure
    assert summary is not None
    assert 'total_alerts' in summary
    assert 'agents_with_alerts' in summary
    assert 'unique_alert_types' in summary
    assert 'by_level' in summary
    assert 'top_keywords' in summary
    
    # Verify values make sense
    assert summary['total_alerts'] > 0
    assert summary['agents_with_alerts'] > 0
    assert summary['unique_alert_types'] >= 0
    assert len(summary['by_level']) > 0
    
    # Verify top keywords
    assert isinstance(summary['top_keywords'], list)
    if summary['top_keywords']:
        for keyword in summary['top_keywords']:
            assert 'keyword' in keyword
            assert 'count' in keyword
            assert keyword['count'] > 0
    
    # Test with filter by agent
    params = MetricParams(agent_ids=["agent-0"])
    filtered_summary = security_metrics.get_security_alerts_summary(params)
    
    # Filtered summary should have fewer alerts
    assert filtered_summary['total_alerts'] < summary['total_alerts']
    
    # Test with time range filter
    time_range = TimeRange(
        start=datetime.utcnow() - timedelta(hours=1),
        end=datetime.utcnow()
    )
    params = MetricParams(time_range=time_range)
    time_filtered_summary = security_metrics.get_security_alerts_summary(params)
    
    # Time filtered summary might have fewer alerts
    assert time_filtered_summary['total_alerts'] <= summary['total_alerts']


def test_get_security_alerts_by_agent(security_metrics):
    """Test getting security alerts by agent."""
    # Test without filters
    result = security_metrics.get_security_alerts_by_agent()
    
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
        assert 'alert_count' in item
        assert 'latest_alert' in item
        
        # Values should be valid
        assert item['alert_count'] > 0


def test_get_security_alerts_time_series(security_metrics):
    """Test getting security alerts time series."""
    # Test with hourly resolution
    params = TimeSeriesParams(resolution=TimeResolution.HOUR)
    time_series = security_metrics.get_security_alerts_time_series(params)
    
    # Verify structure
    assert isinstance(time_series, list)
    
    # May be empty if all events are in same hour
    if time_series:
        for point in time_series:
            assert 'timestamp' in point
            assert 'alert_count' in point
            
            # Values should be valid
            assert point['alert_count'] >= 0
    
    # Test with daily resolution
    params = TimeSeriesParams(resolution=TimeResolution.DAY)
    time_series = security_metrics.get_security_alerts_time_series(params)
    
    if time_series:
        # Timestamp should be in ISO format
        for point in time_series:
            # Should be date format YYYY-MM-DD with optional time
            assert len(point['timestamp']) >= 10


def test_get_security_alerts_by_level(security_metrics):
    """Test getting security alerts by level."""
    # Test without filters
    result = security_metrics.get_security_alerts_by_level()
    
    # Verify structure
    assert result is not None
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')
    
    # Verify content
    assert len(result.items) > 0
    for item in result.items:
        assert 'level' in item
        assert 'alert_count' in item
        assert 'agent_count' in item
        assert 'latest_alert' in item
        
        # Values should be valid
        assert item['level'] in ['low', 'medium', 'high']
        assert item['alert_count'] > 0
        assert item['agent_count'] > 0


def test_get_suspicious_inputs(security_metrics):
    """Test getting suspicious inputs."""
    # Test without filters
    result = security_metrics.get_suspicious_inputs()
    
    # This might return empty if no LLM interactions triggered alerts
    if result.items:
        # Verify structure
        assert hasattr(result, 'items')
        assert hasattr(result, 'total')
        
        for item in result.items:
            assert 'agent_id' in item
            assert 'timestamp' in item
            assert 'severity' in item
            assert 'alert_type' in item
            assert 'input_text' in item
            
            # Values should be valid
            assert item['severity'] in ['low', 'medium', 'high'] 