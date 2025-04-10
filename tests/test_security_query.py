"""
Tests for the security query and analysis implementation.

This module tests that security alerts can be queried flexibly
and that the analysis functions provide the expected results.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.services.security_query import SecurityQueryService
from src.analysis.security_analysis import format_alert_for_response, get_security_overview


@pytest.fixture
def mock_db_with_alerts():
    """Create a mock database session with test alerts."""
    mock_db = MagicMock(spec=Session)
    
    # Create mock alerts for querying
    mock_alerts = []
    for i in range(5):
        alert = MagicMock(spec=SecurityAlert)
        alert.id = i + 1
        alert.timestamp = datetime.utcnow() - timedelta(days=i)
        alert.schema_version = "1.0"
        alert.trace_id = f"trace{i}"
        alert.span_id = f"span{i}"
        alert.event_name = "security.content.dangerous"
        alert.log_level = "SECURITY_ALERT"
        alert.alert_level = ["none", "suspicious", "dangerous", "critical", "dangerous"][i]
        alert.category = ["sensitive_data", "prompt_injection", "malicious_code", "sensitive_data", "prompt_injection"][i]
        alert.severity = ["low", "medium", "high", "critical", "high"][i]
        alert.description = f"Test alert {i+1}"
        alert.llm_vendor = ["openai", "anthropic", "openai", "anthropic", "openai"][i]
        alert.event_id = i + 1
        alert.event = MagicMock(spec=Event)
        alert.event.agent_id = f"agent{i % 2}"  # Two different agents
        
        mock_alerts.append(alert)
    
    # Configure query mock to return our test alerts
    query_mock = MagicMock()
    join_mock = MagicMock()
    filter_mock = MagicMock()
    order_mock = MagicMock()
    limit_mock = MagicMock()
    offset_mock = MagicMock()
    count_mock = MagicMock()
    
    # Setup chaining
    mock_db.query.return_value = query_mock
    query_mock.join.return_value = join_mock
    join_mock.filter.return_value = filter_mock
    filter_mock.filter.return_value = filter_mock
    filter_mock.order_by.return_value = order_mock
    order_mock.limit.return_value = limit_mock
    order_mock.offset.return_value = offset_mock
    limit_mock.all.return_value = mock_alerts
    filter_mock.count.return_value = len(mock_alerts)
    
    # For aggregate queries
    group_mock = MagicMock()
    filter_mock.group_by.return_value = group_mock
    
    # Set up mock results for aggregates
    severity_results = [
        MagicMock(severity="low", count=1),
        MagicMock(severity="medium", count=1),
        MagicMock(severity="high", count=2),
        MagicMock(severity="critical", count=1)
    ]
    
    category_results = [
        MagicMock(category="sensitive_data", count=2),
        MagicMock(category="prompt_injection", count=2),
        MagicMock(category="malicious_code", count=1)
    ]
    
    alert_level_results = [
        MagicMock(alert_level="none", count=1),
        MagicMock(alert_level="suspicious", count=1),
        MagicMock(alert_level="dangerous", count=2),
        MagicMock(alert_level="critical", count=1)
    ]
    
    vendor_results = [
        MagicMock(llm_vendor="openai", count=3),
        MagicMock(llm_vendor="anthropic", count=2)
    ]
    
    # Configure group mock to return different results for different queries
    group_mock.all.side_effect = [
        severity_results,
        category_results,
        alert_level_results,
        vendor_results
    ]
    
    # Time series results
    time_bucket_mock = MagicMock()
    bucket_mock = MagicMock()
    time_bucket_mock.group_by.return_value = bucket_mock
    bucket_mock.order_by.return_value = bucket_mock
    
    time_series_results = [
        MagicMock(bucket=datetime.utcnow() - timedelta(days=2), count=3),
        MagicMock(bucket=datetime.utcnow() - timedelta(days=1), count=1),
        MagicMock(bucket=datetime.utcnow(), count=1)
    ]
    
    bucket_mock.all.return_value = time_series_results
    
    return mock_db


def test_get_alerts(mock_db_with_alerts):
    """Test the get_alerts method of SecurityQueryService."""
    # Call the method
    alerts, count = SecurityQueryService.get_alerts(
        db=mock_db_with_alerts,
        time_start=datetime.utcnow() - timedelta(days=7),
        time_end=datetime.utcnow(),
        severity=["high", "critical"],
        category=["sensitive_data"],
        alert_level=["dangerous", "critical"],
        llm_vendor=["openai"],
        page=1,
        page_size=10
    )
    
    # Verify that query was constructed properly by checking method calls
    mock_db_with_alerts.query.assert_called_once()
    
    # Verify that we got results back
    assert isinstance(alerts, list)
    assert isinstance(count, int)
    assert count == 5  # Our mock is configured to return 5


def test_get_alert_metrics(mock_db_with_alerts):
    """Test the get_alert_metrics method of SecurityQueryService."""
    # Call the method
    metrics = SecurityQueryService.get_alert_metrics(
        db=mock_db_with_alerts,
        time_start=datetime.utcnow() - timedelta(days=7),
        time_end=datetime.utcnow()
    )
    
    # Verify that we got the expected metrics
    assert "total_count" in metrics
    assert "by_severity" in metrics
    assert "by_category" in metrics
    assert "by_alert_level" in metrics
    assert "by_llm_vendor" in metrics
    
    # Check that the counts match our expectations
    assert metrics["by_severity"]["low"] == 1
    assert metrics["by_severity"]["medium"] == 1
    assert metrics["by_severity"]["high"] == 2
    assert metrics["by_severity"]["critical"] == 1
    
    assert metrics["by_category"]["sensitive_data"] == 2
    assert metrics["by_category"]["prompt_injection"] == 2
    assert metrics["by_category"]["malicious_code"] == 1


def test_get_time_series(mock_db_with_alerts):
    """Test the get_time_series method of SecurityQueryService."""
    with patch('src.analysis.utils.sql_time_bucket') as mock_time_bucket:
        # Mock the time bucket function
        mock_time_bucket.return_value = func.date_trunc('day', SecurityAlert.timestamp)
        
        # Call the method
        time_series = SecurityQueryService.get_time_series(
            db=mock_db_with_alerts,
            time_start=datetime.utcnow() - timedelta(days=7),
            time_end=datetime.utcnow(),
            interval="1d"
        )
        
        # Verify that we got results
        assert isinstance(time_series, list)
        assert len(time_series) > 0
        
        # Check structure of the time series points
        for point in time_series:
            assert "timestamp" in point
            assert "count" in point


def test_format_alert_for_response():
    """Test the format_alert_for_response function."""
    # Create a mock alert
    alert = MagicMock(spec=SecurityAlert)
    alert.id = 1
    alert.timestamp = datetime.utcnow()
    alert.schema_version = "1.0"
    alert.trace_id = "trace123"
    alert.span_id = "span123"
    alert.parent_span_id = "parent123"
    alert.event_name = "security.content.dangerous"
    alert.log_level = "SECURITY_ALERT"
    alert.alert_level = "dangerous"
    alert.category = "sensitive_data"
    alert.severity = "high"
    alert.description = "Sensitive data detected"
    alert.llm_vendor = "openai"
    alert.content_sample = "Sample content"
    alert.detection_time = datetime.utcnow()
    alert.keywords = ["keyword1", "keyword2"]
    alert.event_id = 1
    alert.event = MagicMock(spec=Event)
    alert.event.agent_id = "agent123"
    
    # Call the function
    formatted = format_alert_for_response(alert)
    
    # Verify the result
    assert formatted["id"] == 1
    assert "timestamp" in formatted
    assert formatted["schema_version"] == "1.0"
    assert formatted["trace_id"] == "trace123"
    assert formatted["span_id"] == "span123"
    assert formatted["parent_span_id"] == "parent123"
    assert formatted["event_name"] == "security.content.dangerous"
    assert formatted["log_level"] == "SECURITY_ALERT"
    assert formatted["alert_level"] == "dangerous"
    assert formatted["category"] == "sensitive_data"
    assert formatted["severity"] == "high"
    assert formatted["description"] == "Sensitive data detected"
    assert formatted["llm_vendor"] == "openai"
    assert formatted["content_sample"] == "Sample content"
    assert "detection_time" in formatted
    assert formatted["keywords"] == ["keyword1", "keyword2"]
    assert formatted["event_id"] == 1
    assert formatted["agent_id"] == "agent123"


def test_get_security_overview(mock_db_with_alerts):
    """Test the get_security_overview function."""
    # Patch the SecurityQueryService methods
    with patch('src.services.security_query.SecurityQueryService.get_alert_metrics') as mock_metrics, \
         patch('src.services.security_query.SecurityQueryService.get_time_series') as mock_time_series, \
         patch('src.services.security_query.SecurityQueryService.get_alerts') as mock_get_alerts:
        
        # Configure mocks
        mock_metrics.return_value = {
            "total_count": 5,
            "by_severity": {"low": 1, "medium": 1, "high": 2, "critical": 1},
            "by_category": {"sensitive_data": 2, "prompt_injection": 2, "malicious_code": 1},
            "by_alert_level": {"none": 1, "suspicious": 1, "dangerous": 2, "critical": 1},
            "by_llm_vendor": {"openai": 3, "anthropic": 2}
        }
        
        mock_time_series.return_value = [
            {"timestamp": "2024-04-20T00:00:00", "count": 2},
            {"timestamp": "2024-04-21T00:00:00", "count": 3}
        ]
        
        mock_alerts = [MagicMock(spec=SecurityAlert) for _ in range(2)]
        mock_get_alerts.return_value = (mock_alerts, 2)
        
        # Call the function
        overview = get_security_overview(
            db=mock_db_with_alerts,
            time_range="7d"
        )
        
        # Verify the result
        assert "metrics" in overview
        assert "time_series" in overview
        assert "recent_alerts" in overview
        assert "time_range" in overview
        
        assert overview["metrics"]["total_count"] == 5
        assert len(overview["time_series"]) == 2
        assert isinstance(overview["recent_alerts"], list)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 