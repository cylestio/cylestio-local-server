"""
Tests for the security API endpoints.

This module tests that the security API endpoints work correctly.
"""
import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.services.security_query import SecurityQueryService
from src.analysis.security_analysis import format_alert_for_response, get_security_overview


# Create a test client
client = TestClient(app)


@pytest.fixture
def mock_security_alerts():
    """Create mock security alerts for testing."""
    alerts = []
    for i in range(5):
        alert = MagicMock(spec=SecurityAlert)
        alert.id = i + 1
        alert.timestamp = datetime.utcnow() - timedelta(days=i)
        alert.schema_version = "1.0"
        alert.trace_id = f"trace{i}"
        alert.span_id = f"span{i}"
        alert.parent_span_id = None
        alert.event_name = "security.content.dangerous"
        alert.log_level = "SECURITY_ALERT"
        alert.alert_level = ["none", "suspicious", "dangerous", "critical", "dangerous"][i]
        alert.category = ["sensitive_data", "prompt_injection", "malicious_code", "sensitive_data", "prompt_injection"][i]
        alert.severity = ["low", "medium", "high", "critical", "high"][i]
        alert.description = f"Test alert {i+1}"
        alert.llm_vendor = ["openai", "anthropic", "openai", "anthropic", "openai"][i]
        alert.content_sample = f"Sample content {i+1}"
        alert.detection_time = datetime.utcnow() - timedelta(days=i, hours=1)
        alert.keywords = [f"keyword{i}:{i}"]
        alert.event_id = i + 1
        alert.event = MagicMock(spec=Event)
        alert.event.agent_id = f"agent{i % 2}"  # Two different agents
        
        alerts.append(alert)
    
    return alerts


@pytest.fixture
def mock_metrics():
    """Create mock security metrics for testing."""
    return {
        "total_count": 5,
        "by_severity": {"low": 1, "medium": 1, "high": 2, "critical": 1},
        "by_category": {"sensitive_data": 2, "prompt_injection": 2, "malicious_code": 1},
        "by_alert_level": {"none": 1, "suspicious": 1, "dangerous": 2, "critical": 1},
        "by_llm_vendor": {"openai": 3, "anthropic": 2}
    }


@pytest.fixture
def mock_time_series():
    """Create mock time series data for testing."""
    return [
        {"timestamp": "2024-04-20T00:00:00", "count": 2},
        {"timestamp": "2024-04-21T00:00:00", "count": 3}
    ]


@patch('src.services.security_query.SecurityQueryService.get_alerts')
def test_get_security_alerts(mock_get_alerts, mock_security_alerts, mock_metrics):
    """Test the GET /v1/alerts endpoint."""
    # Configure the mock
    mock_get_alerts.return_value = (mock_security_alerts, len(mock_security_alerts))
    
    # Call the API
    with patch('src.services.security_query.SecurityQueryService.get_alert_metrics', return_value=mock_metrics):
        response = client.get("/v1/alerts?time_range=7d&severity=high,critical")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total_count" in data
    assert "metrics" in data
    assert "pagination" in data
    assert "time_range" in data
    assert "filters" in data
    
    # Check that we got the right number of alerts
    assert len(data["alerts"]) == len(mock_security_alerts)
    
    # Verify metrics format
    assert "by_severity" in data["metrics"]
    assert "by_category" in data["metrics"]
    assert "by_alert_level" in data["metrics"]
    assert "by_llm_vendor" in data["metrics"]


@patch('src.services.security_query.SecurityQueryService.get_time_series')
def test_get_security_alerts_timeseries(mock_get_time_series, mock_time_series):
    """Test the GET /v1/alerts/timeseries endpoint."""
    # Configure the mock
    mock_get_time_series.return_value = mock_time_series
    
    # Call the API
    response = client.get("/v1/alerts/timeseries?time_range=7d&interval=1d")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    
    # Verify time series format
    assert "time_series" in data
    assert "time_range" in data
    assert "interval" in data
    assert "filters" in data
    
    # Check the values
    assert len(data["time_series"]) == len(mock_time_series)
    assert data["interval"] == "1d"
    

@patch('src.analysis.security_analysis.get_security_overview')
def test_get_security_dashboard_overview(mock_get_overview, mock_metrics, mock_time_series, mock_security_alerts):
    """Test the GET /v1/overview endpoint."""
    # Prepare mock overview data
    mock_overview = {
        "metrics": mock_metrics,
        "time_series": mock_time_series,
        "recent_alerts": [format_alert_for_response(alert) for alert in mock_security_alerts[:2]],
        "time_range": {
            "from": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "to": datetime.utcnow().isoformat(),
            "description": "Last 7d"
        }
    }
    
    # Configure the mock
    mock_get_overview.return_value = mock_overview
    
    # Call the API
    response = client.get("/v1/overview?time_range=7d")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    
    # Verify overview format
    assert "metrics" in data
    assert "time_series" in data
    assert "recent_alerts" in data
    assert "time_range" in data
    
    # Check values
    assert data["metrics"] == mock_metrics
    assert len(data["time_series"]) == len(mock_time_series)
    assert len(data["recent_alerts"]) == 2
    assert data["time_range"]["description"] == "Last 7d"


def test_invalid_time_range():
    """Test that an invalid time_range returns a 400 error."""
    response = client.get("/v1/alerts?time_range=invalid")
    assert response.status_code == 400
    assert "Invalid time_range value" in response.json()["detail"]


def test_get_security_alert_details(mock_security_alerts):
    """Test the GET /v1/alerts/{alert_id} endpoint."""
    # Create a mock response for format_alert_for_response
    mock_alert_data = {
        "id": 12345,  # Use a high ID number to avoid conflicts
        "timestamp": datetime.utcnow().isoformat(),
        "schema_version": "1.0",
        "alert_level": "none",
        "category": "sensitive_data",
        "severity": "low",
        "description": "Test alert 1"
    }
    
    # Patch both the database dependency and the formatter function
    with patch('src.database.session.get_db'), \
         patch('src.api.routes.security.format_alert_for_response', return_value=mock_alert_data), \
         patch('sqlalchemy.orm.query.Query.filter'), \
         patch('sqlalchemy.orm.query.Query.first', return_value=mock_security_alerts[0]):
            
        # Use a high numeric ID to avoid conflict with 'timeseries'
        response = client.get("/v1/alerts/12345")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    
    # Verify alert details from our mocked formatter
    assert data["id"] == 12345
    assert "timestamp" in data
    assert data["schema_version"] == "1.0"
    assert data["alert_level"] == "none"
    assert data["category"] == "sensitive_data"
    assert data["severity"] == "low"
    assert data["description"] == "Test alert 1"


def test_get_nonexistent_alert():
    """Test that requesting a non-existent alert returns a 404 error."""
    with patch('src.database.session.get_db'), \
         patch('sqlalchemy.orm.query.Query.filter'), \
         patch('sqlalchemy.orm.query.Query.first', return_value=None):
        response = client.get("/v1/alerts/99999")
    
    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_security_alert_triggers(mock_security_alerts):
    """Test the GET /v1/alerts/{alert_id}/triggers endpoint."""
    # Create a mock triggers list
    mock_triggers = [
        MagicMock(triggering_event_id=101),
        MagicMock(triggering_event_id=102),
        MagicMock(triggering_event_id=103)
    ]
    
    # Patch the necessary functions and queries
    with patch('src.database.session.get_db'), \
         patch('sqlalchemy.orm.query.Query.filter'), \
         patch('sqlalchemy.orm.query.Query.first', return_value=mock_security_alerts[0]), \
         patch('sqlalchemy.orm.query.Query.all', return_value=mock_triggers):
            
        response = client.get("/v1/alerts/12345/triggers")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "alert_id" in data
    assert "triggered_event_ids" in data
    assert "count" in data
    
    # Verify the contents
    assert data["alert_id"] == 12345
    assert len(data["triggered_event_ids"]) == 3
    assert data["triggered_event_ids"] == [101, 102, 103]
    assert data["count"] == 3


def test_get_nonexistent_alert_triggers():
    """Test that requesting triggers for a non-existent alert returns a 404 error."""
    with patch('src.database.session.get_db'), \
         patch('sqlalchemy.orm.query.Query.filter'), \
         patch('sqlalchemy.orm.query.Query.first', return_value=None):
        response = client.get("/v1/alerts/99999/triggers")
    
    # Check the response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 