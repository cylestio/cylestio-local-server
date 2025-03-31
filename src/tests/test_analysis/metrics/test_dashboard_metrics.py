"""
Tests for dashboard metrics.
"""
import pytest
from datetime import datetime, timedelta

from analysis.metrics import DashboardMetrics
from analysis.interface import MetricParams, TimeSeriesParams, TimeResolution, TimeRange


@pytest.fixture
def dashboard_metrics(db_session, mock_data):
    """Create dashboard metrics instance."""
    return DashboardMetrics(db_session)


def test_get_summary_metrics(dashboard_metrics):
    """Test getting summary metrics for the dashboard."""
    # Test without filters
    summary = dashboard_metrics.get_summary_metrics()
    
    # Verify basic structure
    assert summary is not None
    assert 'agents' in summary
    assert 'sessions' in summary
    assert 'llm' in summary
    assert 'tools' in summary
    assert 'security' in summary
    
    # Check agents section
    assert 'total' in summary['agents']
    assert 'active_last_24h' in summary['agents']
    assert 'active_last_7d' in summary['agents']
    assert summary['agents']['total'] > 0
    
    # Check sessions section
    assert 'total' in summary['sessions']
    assert 'active' in summary['sessions']
    assert 'average_duration_ms' in summary['sessions']
    assert summary['sessions']['total'] > 0
    
    # Check LLM section
    assert 'total_calls' in summary['llm']
    assert 'total_tokens' in summary['llm']
    assert 'estimated_cost' in summary['llm']
    assert 'unique_models' in summary['llm']
    assert summary['llm']['total_calls'] > 0
    assert summary['llm']['total_tokens'] > 0
    
    # Check tools section
    assert 'total_calls' in summary['tools']
    assert 'unique_tools' in summary['tools']
    assert 'success_rate' in summary['tools']
    assert summary['tools']['total_calls'] > 0
    assert summary['tools']['unique_tools'] > 0
    
    # Check security section
    assert 'total_alerts' in summary['security']
    assert 'high_severity' in summary['security']
    assert 'last_24h' in summary['security']
    assert summary['security']['total_alerts'] > 0
    
    # Test with filter by agent
    params = MetricParams(agent_ids=["agent-0"])
    filtered_summary = dashboard_metrics.get_summary_metrics(params)
    
    # Filtered summary should have fewer calls
    assert filtered_summary['llm']['total_calls'] < summary['llm']['total_calls']
    
    # Test with time range filter
    time_range = TimeRange(
        start=datetime.utcnow() - timedelta(hours=1),
        end=datetime.utcnow()
    )
    params = MetricParams(time_range=time_range)
    time_filtered_summary = dashboard_metrics.get_summary_metrics(params)
    
    # Time filtered summary might have fewer calls
    assert time_filtered_summary['llm']['total_calls'] <= summary['llm']['total_calls']


def test_get_activity_timeline(dashboard_metrics):
    """Test getting activity timeline."""
    # Test with hourly resolution
    params = TimeSeriesParams(resolution=TimeResolution.HOUR)
    timeline = dashboard_metrics.get_activity_timeline(params)
    
    # Verify structure
    assert isinstance(timeline, list)
    
    # May be empty if all events are in same hour
    if timeline:
        for point in timeline:
            assert 'timestamp' in point
            assert 'llm_count' in point
            assert 'tool_count' in point
            assert 'security_count' in point
            assert 'monitoring_count' in point
            assert 'other_count' in point
            assert 'total_count' in point
            
            # Total should equal sum of individual counts
            assert point['total_count'] == (
                point['llm_count'] + 
                point['tool_count'] + 
                point['security_count'] + 
                point['monitoring_count'] + 
                point['other_count']
            )
    
    # Test with daily resolution
    params = TimeSeriesParams(resolution=TimeResolution.DAY)
    timeline = dashboard_metrics.get_activity_timeline(params)
    
    if timeline:
        # Timestamp should be in ISO format
        for point in timeline:
            # Should be date format YYYY-MM-DD with optional time
            assert len(point['timestamp']) >= 10


def test_get_recent_sessions(dashboard_metrics):
    """Test getting recent sessions."""
    # Test without filters
    result = dashboard_metrics.get_recent_sessions()
    
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
        assert 'session_id' in item
        assert 'agent_id' in item
        assert 'start_timestamp' in item
        assert 'end_timestamp' in item  # May be None for active sessions
        assert 'duration_ms' in item    # May be None for active sessions
        assert 'status' in item
        assert 'event_count' in item
        assert 'llm_event_count' in item
        assert 'tool_event_count' in item
        assert 'security_event_count' in item
        
        # Status should be valid
        assert item['status'] in ['active', 'completed']
        
        # Timestamps should be in ISO format
        if item['start_timestamp']:
            assert 'T' in item['start_timestamp']
        if item['end_timestamp']:
            assert 'T' in item['end_timestamp']
        
        # For completed sessions, duration should be positive
        if item['status'] == 'completed':
            assert item['duration_ms'] > 0


def test_get_agent_performance(dashboard_metrics):
    """Test getting agent performance metrics."""
    # Test without filters
    result = dashboard_metrics.get_agent_performance()
    
    # Verify structure
    assert result is not None
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')
    
    # Verify content
    assert len(result.items) > 0
    for item in result.items:
        assert 'agent_id' in item
        assert 'llm_call_count' in item
        assert 'avg_llm_duration_ms' in item
        assert 'tool_call_count' in item
        assert 'avg_tool_duration_ms' in item
        assert 'security_alert_count' in item
        assert 'total_events' in item
        
        # Total events should equal the sum of individual counts
        assert item['total_events'] == (
            item['llm_call_count'] + 
            item['tool_call_count'] + 
            item['security_alert_count']
        )
        
        # For agents with LLM calls, average duration should be positive
        if item['llm_call_count'] > 0 and item['avg_llm_duration_ms'] is not None:
            assert item['avg_llm_duration_ms'] > 0
        
        # For agents with tool calls, average duration should be positive
        if item['tool_call_count'] > 0 and item['avg_tool_duration_ms'] is not None:
            assert item['avg_tool_duration_ms'] > 0 