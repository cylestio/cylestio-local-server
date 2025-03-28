"""
Tests for attribute models.

This module contains tests for the attribute models:
- ToolAttribute
- SecurityAttribute
- FrameworkAttribute
"""
import pytest
from unittest.mock import MagicMock

from src.models.tool_attribute import ToolAttribute
from src.models.security_attribute import SecurityAttribute
from src.models.framework_attribute import FrameworkAttribute


class TestToolAttribute:
    """Tests for the ToolAttribute model."""
    
    def test_create_from_dict(self):
        """Test creating tool attributes from a dictionary."""
        # Mock the database session
        db_session = MagicMock()
        
        # Create test data
        tool_interaction_id = 1
        attributes = {
            "string_attr": "test value",
            "int_attr": 42,
            "float_attr": 3.14,
            "bool_attr": True,
            "none_attr": None  # Should be skipped
        }
        
        # Create attributes from dictionary
        result = ToolAttribute.create_from_dict(db_session, tool_interaction_id, attributes)
        
        # Check that add_all was called
        db_session.add_all.assert_called_once()
        
        # Check that 4 attributes were created (none_attr should be skipped)
        assert len(result) == 4
        
        # Check that the attributes were set correctly
        attrs_by_key = {attr.key: attr for attr in result}
        
        assert "string_attr" in attrs_by_key
        assert attrs_by_key["string_attr"].value_type == "text"
        assert attrs_by_key["string_attr"].value_text == "test value"
        
        assert "int_attr" in attrs_by_key
        assert attrs_by_key["int_attr"].value_type == "numeric"
        assert attrs_by_key["int_attr"].value_numeric == 42
        
        assert "float_attr" in attrs_by_key
        assert attrs_by_key["float_attr"].value_type == "numeric"
        assert attrs_by_key["float_attr"].value_numeric == 3.14
        
        assert "bool_attr" in attrs_by_key
        assert attrs_by_key["bool_attr"].value_type == "boolean"
        assert attrs_by_key["bool_attr"].value_boolean is True
        
        assert "none_attr" not in attrs_by_key
    
    def test_value_property(self):
        """Test the value property for different types."""
        # Test text attribute
        text_attr = ToolAttribute(key="text_key", value_type="text", value_text="text value")
        assert text_attr.value == "text value"
        
        # Test numeric attribute
        numeric_attr = ToolAttribute(key="numeric_key", value_type="numeric", value_numeric=42.5)
        assert numeric_attr.value == 42.5
        
        # Test boolean attribute
        bool_attr = ToolAttribute(key="bool_key", value_type="boolean", value_boolean=True)
        assert bool_attr.value is True
        
        # Test invalid type
        invalid_attr = ToolAttribute(key="invalid_key", value_type="invalid")
        assert invalid_attr.value is None


class TestSecurityAttribute:
    """Tests for the SecurityAttribute model."""
    
    def test_create_security_attributes(self):
        """Test creating security attributes."""
        # Mock the database session
        db_session = MagicMock()
        
        # Create test data
        security_alert_id = 1
        attributes = {
            "detection_method": "pattern matching",
            "confidence_score": 0.95,
            "is_critical": True
        }
        
        # Create attributes
        result = SecurityAttribute.create_security_attributes(
            db_session, security_alert_id, attributes
        )
        
        # Check that add_all was called
        db_session.add_all.assert_called_once()
        
        # Check that 3 attributes were created
        assert len(result) == 3
        
        # Check that the attributes were set correctly
        attrs_by_key = {attr.key: attr for attr in result}
        
        assert attrs_by_key["detection_method"].value == "pattern matching"
        assert attrs_by_key["confidence_score"].value == 0.95
        assert attrs_by_key["is_critical"].value is True


class TestFrameworkAttribute:
    """Tests for the FrameworkAttribute model."""
    
    def test_to_dict(self):
        """Test converting attributes to a dictionary."""
        # Create mock data
        framework_event_id = 1
        
        attr1 = FrameworkAttribute(
            framework_event_id=framework_event_id,
            key="version",
            value_type="text",
            value_text="1.0.0"
        )
        
        attr2 = FrameworkAttribute(
            framework_event_id=framework_event_id,
            key="startup_time_ms",
            value_type="numeric",
            value_numeric=150.5
        )
        
        attr3 = FrameworkAttribute(
            framework_event_id=framework_event_id,
            key="debug_mode",
            value_type="boolean",
            value_boolean=False
        )
        
        # Mock database session
        db_session = MagicMock()
        db_session.query().filter().all.return_value = [attr1, attr2, attr3]
        
        # Test to_dict method
        result = FrameworkAttribute.to_dict(db_session, framework_event_id)
        
        # Check the result
        assert result == {
            "version": "1.0.0",
            "startup_time_ms": 150.5,
            "debug_mode": False
        } 