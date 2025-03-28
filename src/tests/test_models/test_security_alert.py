"""
Tests for the SecurityAlert model.
"""
import json
import datetime
import pytest

from src.models.agent import Agent
from src.models.event import Event
from src.models.security_alert import SecurityAlert


@pytest.fixture
def test_agent(db_session):
    """Create a test agent for use in security alert tests."""
    agent = Agent(
        agent_id="test-security-agent",
        name="Test Security Agent",
        first_seen=datetime.datetime.utcnow(),
        last_seen=datetime.datetime.utcnow()
    )
    db_session.add(agent)
    db_session.commit()
    return agent


@pytest.fixture
def test_event(db_session, test_agent):
    """Create a test event for use in security alert tests."""
    event = Event(
        agent_id=test_agent.id,
        timestamp=datetime.datetime.utcnow(),
        schema_version="1.0",
        name="security.alert",
        level="WARNING",
        event_type="security"
    )
    db_session.add(event)
    db_session.commit()
    return event


def test_security_alert_creation(db_session, test_event):
    """Test creating a new security alert."""
    # Create a new security alert
    security_alert = SecurityAlert(
        event_id=test_event.id,
        alert_type="credential_exposure",
        severity="MEDIUM",
        description="API key exposed in code",
        context=json.dumps({
            "line": 42,
            "file": "config.py",
            "matched_text": "API_KEY = 'sk_test_1234567890'"
        })
    )
    
    db_session.add(security_alert)
    db_session.commit()
    
    # Query the security alert
    saved_alert = db_session.query(SecurityAlert).filter(
        SecurityAlert.event_id == test_event.id
    ).first()
    
    # Verify
    assert saved_alert is not None
    assert saved_alert.event_id == test_event.id
    assert saved_alert.alert_type == "credential_exposure"
    assert saved_alert.severity == "MEDIUM"
    assert saved_alert.description == "API key exposed in code"
    assert json.loads(saved_alert.context) == {
        "line": 42,
        "file": "config.py",
        "matched_text": "API_KEY = 'sk_test_1234567890'"
    }
    assert saved_alert.status == "OPEN"
    assert saved_alert.resolved_at is None
    assert saved_alert.resolution_notes is None


def test_security_alert_relationships(db_session, test_event):
    """Test security alert relationships."""
    # Create a new security alert
    security_alert = SecurityAlert(
        event_id=test_event.id,
        alert_type="insecure_import",
        severity="LOW",
        description="Importing an insecure module"
    )
    
    db_session.add(security_alert)
    db_session.commit()
    
    # Verify the relationship with the event
    assert security_alert.event.id == test_event.id
    assert security_alert.event.name == "security.alert"
    
    # Verify from the other direction (event to security alert)
    assert test_event.security_alert.id == security_alert.id
    assert test_event.security_alert.alert_type == "insecure_import"


def test_from_event(db_session, test_event):
    """Test creating a security alert from an event."""
    # Create event data for security alert
    event_data = {
        "name": "security.alert",
        "payload": {
            "alert_type": "sql_injection",
            "severity": "HIGH",
            "description": "Potential SQL injection in user input",
            "context": {
                "input_field": "search_query",
                "user_input": "'; DROP TABLE users; --",
                "endpoint": "/api/search"
            }
        }
    }
    
    # Update the test event with this data
    test_event.data = json.dumps(event_data)
    db_session.commit()
    
    # Create security alert from event
    security_alert = SecurityAlert.from_event(db_session, test_event)
    
    # Verify
    assert security_alert is not None
    assert security_alert.event_id == test_event.id
    assert security_alert.alert_type == "sql_injection"
    assert security_alert.severity == "HIGH"
    assert security_alert.description == "Potential SQL injection in user input"
    assert security_alert.context is not None
    
    context_dict = json.loads(security_alert.context)
    assert context_dict["input_field"] == "search_query"
    assert context_dict["user_input"] == "'; DROP TABLE users; --"
    assert context_dict["endpoint"] == "/api/search"
    
    assert security_alert.status == "OPEN"
    assert security_alert.resolved_at is None
    assert security_alert.resolution_notes is None


def test_resolve_alert(db_session, test_event):
    """Test resolving a security alert."""
    # Create a new security alert
    security_alert = SecurityAlert(
        event_id=test_event.id,
        alert_type="xss_vulnerability",
        severity="HIGH",
        description="Unescaped HTML output"
    )
    
    db_session.add(security_alert)
    db_session.commit()
    
    # Verify initial status
    assert security_alert.status == "OPEN"
    assert security_alert.resolved_at is None
    assert security_alert.resolution_notes is None
    
    # Resolve the alert
    resolution_time = datetime.datetime.utcnow()
    security_alert.resolve("Fixed by escaping HTML output", resolution_time)
    db_session.commit()
    
    # Query the security alert
    updated_alert = db_session.query(SecurityAlert).filter(
        SecurityAlert.id == security_alert.id
    ).first()
    
    # Verify resolution
    assert updated_alert.status == "RESOLVED"
    assert updated_alert.resolved_at == resolution_time
    assert updated_alert.resolution_notes == "Fixed by escaping HTML output"


def test_get_context_dict(db_session, test_event):
    """Test the get_context_dict method."""
    # Create a security alert with JSON context
    security_alert = SecurityAlert(
        event_id=test_event.id,
        alert_type="sensitive_data_access",
        severity="HIGH",
        description="Unauthorized access to sensitive data",
        context=json.dumps({
            "user_id": "12345",
            "data_type": "PII",
            "accessed_fields": ["ssn", "dob", "address"],
            "access_time": "2023-01-15T14:30:45Z"
        })
    )
    
    db_session.add(security_alert)
    db_session.commit()
    
    # Get context as dictionary
    context_dict = security_alert.get_context_dict()
    
    # Verify
    assert isinstance(context_dict, dict)
    assert context_dict["user_id"] == "12345"
    assert context_dict["data_type"] == "PII"
    assert context_dict["accessed_fields"] == ["ssn", "dob", "address"]
    assert context_dict["access_time"] == "2023-01-15T14:30:45Z"


def test_get_context_dict_with_invalid_json(db_session, test_event):
    """Test the get_context_dict method with invalid JSON."""
    # Create a security alert with invalid JSON context
    security_alert = SecurityAlert(
        event_id=test_event.id,
        alert_type="test_alert",
        severity="LOW",
        description="Test alert",
        context="{not valid json}"
    )
    
    db_session.add(security_alert)
    db_session.commit()
    
    # Get context as dictionary should return None for invalid JSON
    context_dict = security_alert.get_context_dict()
    
    # Verify
    assert context_dict is None


def test_open_alerts_for_agent(db_session, test_agent):
    """Test the open_alerts_for_agent class method."""
    # Create multiple events for the agent
    for i in range(3):
        event = Event(
            agent_id=test_agent.id,
            timestamp=datetime.datetime.utcnow(),
            schema_version="1.0",
            name=f"security.alert.{i}",
            level="WARNING",
            event_type="security"
        )
        db_session.add(event)
    db_session.commit()
    
    # Get all events for this agent
    agent_events = db_session.query(Event).filter(
        Event.agent_id == test_agent.id
    ).all()
    
    # Create security alerts with different statuses
    alerts = []
    for i, event in enumerate(agent_events):
        alert = SecurityAlert(
            event_id=event.id,
            alert_type=f"test_alert_{i}",
            severity="MEDIUM",
            description=f"Test alert {i}"
        )
        db_session.add(alert)
        alerts.append(alert)
    
    # Resolve one of the alerts
    alerts[1].resolve("Fixed in testing")
    db_session.commit()
    
    # Get open alerts for the agent
    open_alerts = SecurityAlert.open_alerts_for_agent(db_session, test_agent.id)
    
    # Verify
    assert len(open_alerts) == 2  # Only 2 alerts should be open
    assert all(alert.status == "OPEN" for alert in open_alerts)
    
    # Verify the correct alerts are returned
    open_alert_types = [alert.alert_type for alert in open_alerts]
    assert "test_alert_0" in open_alert_types
    assert "test_alert_2" in open_alert_types
    assert "test_alert_1" not in open_alert_types  # This one was resolved 