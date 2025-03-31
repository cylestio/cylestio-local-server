"""
Comprehensive tests for the SecurityAlert model.

These tests validate the SecurityAlert model's functionality,
including data extraction logic, field population, and relationships.
"""
import json
import datetime
import pytest

from sqlalchemy import func
from models.security_alert import SecurityAlert
from models.llm_interaction import LLMInteraction
from tests.test_utils import (
    generate_agent, generate_event, generate_security_alert_data,
    generate_llm_interaction_data
)


class TestSecurityAlertBasic:
    """Basic tests for SecurityAlert model."""
    
    def test_security_alert_creation(self, db_session, test_security_alert_event):
        """Test creating a new security alert."""
        # Create a new security alert
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            source="content_filter",
            alert_timestamp=datetime.datetime.utcnow(),
            details={"policy": "harmful_content", "score": 0.85}
        )
        
        db_session.add(security_alert)
        db_session.commit()
        
        # Query the security alert
        saved_alert = db_session.query(SecurityAlert).filter(
            SecurityAlert.id == security_alert.id
        ).first()
        
        # Verify
        assert saved_alert is not None
        assert saved_alert.event_id == test_security_alert_event.id
        assert saved_alert.alert_type == "content_policy_violation"
        assert saved_alert.severity == "medium"
        assert saved_alert.source == "content_filter"
        assert saved_alert.alert_timestamp is not None
        assert saved_alert.details == {"policy": "harmful_content", "score": 0.85}
        assert saved_alert.flagged_content is None
        assert saved_alert.related_interaction_id is None


class TestSecurityAlertFromEvent:
    """Tests for creating SecurityAlert from event data."""
    
    def test_from_event_basic(self, db_session, test_security_alert_event):
        """Test creating a security alert from an event."""
        # Create telemetry data
        telemetry_data = generate_security_alert_data()
        
        # Create security alert from event
        security_alert = SecurityAlert.from_event(db_session, test_security_alert_event, telemetry_data)
        
        # Verify basic fields
        assert security_alert is not None
        assert security_alert.event_id == test_security_alert_event.id
        assert security_alert.alert_type == "content_policy_violation"
        assert security_alert.severity == "medium"
        assert security_alert.source == "content_filter"
        assert security_alert.alert_timestamp is not None
        assert security_alert.details is not None
        assert security_alert.details["policy"] == "harmful_content"
        assert security_alert.details["score"] == 0.85
        assert security_alert.flagged_content == "This is potentially harmful content"
    
    def test_from_event_missing_fields(self, db_session, test_security_alert_event):
        """Test handling of missing fields in event data."""
        # Create minimal telemetry data with missing fields
        telemetry_data = {
            "attributes": {
                "security.alert.type": "content_policy_violation"
                # Missing severity, source, details, etc.
            }
        }
        
        # Create security alert from event
        security_alert = SecurityAlert.from_event(db_session, test_security_alert_event, telemetry_data)
        
        # Verify it handles missing fields gracefully
        assert security_alert is not None
        assert security_alert.event_id == test_security_alert_event.id
        assert security_alert.alert_type == "content_policy_violation"
        assert security_alert.severity is None
        assert security_alert.source is None
        assert security_alert.details is None
    
    def test_from_event_with_related_llm(self, db_session, test_security_alert_event, test_llm_events):
        """Test creating a security alert with related LLM interaction."""
        # First create an LLM interaction
        start_event, _ = test_llm_events
        llm_data = generate_llm_interaction_data(interaction_type="start")
        llm_interaction = LLMInteraction.from_event(db_session, start_event, llm_data)
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Now create security alert with reference to the LLM interaction
        security_data = generate_security_alert_data()
        # Add reference to LLM interaction
        security_data["attributes"]["security.alert.related_llm_interaction_id"] = llm_interaction.id
        
        # Create security alert from event
        security_alert = SecurityAlert.from_event(db_session, test_security_alert_event, security_data)
        db_session.add(security_alert)
        db_session.commit()
        
        # Verify relationship
        assert security_alert.related_interaction_id == llm_interaction.id
        assert security_alert.related_llm_interaction.id == llm_interaction.id


class TestSecurityAlertRelationships:
    """Tests for security alert relationships."""
    
    def test_security_alert_event_relationship(self, db_session, test_security_alert_event):
        """Test relationship between security alert and Event."""
        # Create a security alert
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            source="content_filter"
        )
        
        db_session.add(security_alert)
        db_session.commit()
        
        # Query the security alert
        saved_alert = db_session.query(SecurityAlert).filter(
            SecurityAlert.id == security_alert.id
        ).first()
        
        # Verify relationships
        assert saved_alert.event.id == test_security_alert_event.id
        assert test_security_alert_event.security_alert.id == saved_alert.id
    
    def test_security_alert_llm_relationship(self, db_session, test_security_alert_event, test_llm_events):
        """Test relationship between security alert and LLM interaction."""
        # Create an LLM interaction
        start_event, _ = test_llm_events
        llm_interaction = LLMInteraction(
            event_id=start_event.id,
            interaction_type="start",
            vendor="anthropic",
            model="claude-3-haiku-20240307"
        )
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Create a security alert with related LLM interaction
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            source="content_filter",
            related_interaction_id=llm_interaction.id
        )
        db_session.add(security_alert)
        db_session.commit()
        
        # Query the security alert
        saved_alert = db_session.query(SecurityAlert).filter(
            SecurityAlert.id == security_alert.id
        ).first()
        
        # Verify relationships
        assert saved_alert.related_interaction_id == llm_interaction.id
        assert saved_alert.related_llm_interaction.id == llm_interaction.id


class TestSecurityAlertUtilityMethods:
    """Tests for SecurityAlert utility methods."""
    
    def test_get_flagged_content(self, db_session, test_security_alert_event):
        """Test extracting flagged content from details."""
        # Test with flagged_content in details
        alert1 = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            details={"flagged_content": "This content is flagged"}
        )
        db_session.add(alert1)
        
        # Test with flagged_text in details
        alert2 = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            details={"flagged_text": "This text is flagged"}
        )
        db_session.add(alert2)
        
        # Test with content_fragment in details
        alert3 = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            details={"content_fragment": "This fragment is flagged"}
        )
        db_session.add(alert3)
        
        db_session.commit()
        
        # Verify extraction
        assert alert1.get_flagged_content() == "This content is flagged"
        assert alert2.get_flagged_content() == "This text is flagged"
        assert alert3.get_flagged_content() == "This fragment is flagged"
    
    def test_compare_flagged_content(self, db_session, test_security_alert_event, test_llm_events):
        """Test comparing flagged content with LLM content."""
        # Create an LLM interaction with content
        start_event, _ = test_llm_events
        llm_interaction = LLMInteraction(
            event_id=start_event.id,
            interaction_type="start",
            vendor="anthropic",
            model="claude-3-haiku-20240307",
            request_data={"messages": [{"role": "user", "content": "This is harmful content"}]}
        )
        db_session.add(llm_interaction)
        db_session.commit()
        
        # Create a security alert with flagged content
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            source="content_filter",
            related_interaction_id=llm_interaction.id,
            flagged_content="harmful content"
        )
        db_session.add(security_alert)
        db_session.commit()
        
        # Test content comparison - should find a match
        assert security_alert.is_content_in_llm_request()
        
        # Create another alert with content not in LLM
        security_alert2 = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            source="content_filter",
            related_interaction_id=llm_interaction.id,
            flagged_content="something completely different"
        )
        db_session.add(security_alert2)
        db_session.commit()
        
        # Test content comparison - should not find a match
        assert not security_alert2.is_content_in_llm_request()


class TestSecurityAlertEdgeCases:
    """Tests for security alert edge cases."""
    
    def test_malformed_details(self, db_session, test_security_alert_event):
        """Test handling of malformed details field."""
        # Test with non-dict details
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            details="not a dictionary"  # String instead of dict
        )
        db_session.add(security_alert)
        db_session.commit()
        
        # Verify it doesn't crash when accessing details
        assert security_alert.details == "not a dictionary"
        
        # Verify utility methods handle it gracefully
        assert security_alert.get_flagged_content() is None
        
        # Test with None details
        security_alert2 = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            details=None
        )
        db_session.add(security_alert2)
        db_session.commit()
        
        # Verify it doesn't crash when accessing None details
        assert security_alert2.details is None
        assert security_alert2.get_flagged_content() is None
    
    def test_missing_relationship(self, db_session, test_security_alert_event):
        """Test handling of non-existent related interaction."""
        # Create a security alert with a non-existent related interaction ID
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type="content_policy_violation",
            severity="medium",
            related_interaction_id=999999  # Non-existent ID
        )
        db_session.add(security_alert)
        db_session.commit()
        
        # Verify it doesn't crash when accessing non-existent relationship
        assert security_alert.related_interaction_id == 999999
        assert security_alert.related_llm_interaction is None  # Should be None for non-existent ID
        
        # Verify utility methods handle missing relationship
        assert not security_alert.is_content_in_llm_request()  # Should return False when no LLM


@pytest.mark.parametrize("alert_type,severity", [
    ("content_policy_violation", "low"),
    ("content_policy_violation", "medium"),
    ("content_policy_violation", "high"),
    ("prompt_injection", "low"),
    ("prompt_injection", "medium"),
    ("prompt_injection", "high"),
    ("pii_detection", "medium"),
    ("jailbreak_attempt", "high"),
    ("malicious_code", "high")
])
class TestSecurityAlertParameterized:
    """Parameterized tests for different alert types and severities."""
    
    def test_alert_type_severity_combinations(self, db_session, test_security_alert_event, alert_type, severity):
        """Test various alert type and severity combinations."""
        # Create security alert with specific type/severity
        security_alert = SecurityAlert(
            event_id=test_security_alert_event.id,
            alert_type=alert_type,
            severity=severity,
            source="test_source"
        )
        
        db_session.add(security_alert)
        db_session.commit()
        
        # Verify
        saved_alert = db_session.query(SecurityAlert).filter(
            SecurityAlert.id == security_alert.id
        ).first()
        
        assert saved_alert is not None
        assert saved_alert.alert_type == alert_type
        assert saved_alert.severity == severity 