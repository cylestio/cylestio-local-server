"""
Tests for the SecurityAlert model schema.

This module tests that the SecurityAlert model has all the required fields
for the new OpenTelemetry-compliant security events format.
"""
import pytest
from datetime import datetime
from sqlalchemy.inspection import inspect

from src.models.security_alert import SecurityAlert
from src.models.event import Event
from src.database.session import get_db


def test_security_alert_model_fields():
    """Test that the SecurityAlert model has all required fields."""
    # Get all column names from the SecurityAlert model
    mapper = inspect(SecurityAlert)
    columns = [column.name for column in mapper.columns]
    
    # Check required fields from OpenTelemetry format
    required_fields = [
        'id', 'event_id', 'schema_version', 'timestamp', 
        'trace_id', 'span_id', 'parent_span_id', 'event_name', 
        'log_level', 'alert_level', 'category', 'severity', 
        'description', 'llm_vendor', 'content_sample', 
        'detection_time', 'keywords'
    ]
    
    for field in required_fields:
        assert field in columns, f"Required field '{field}' missing from SecurityAlert model"


def test_security_alert_relationships():
    """Test the relationships in the SecurityAlert model."""
    # Check that the relationship to Event is properly defined
    assert hasattr(SecurityAlert, 'event'), "SecurityAlert should have a relationship to Event"


def test_security_alert_indexes():
    """Test that the appropriate indexes are defined."""
    # Get all indexes from the SecurityAlert model
    mapper = inspect(SecurityAlert)
    
    # Check if event_id is indexed (foreign key constraint may create an index)
    indexes = {index.name: [column.name for column in index.columns] 
               for index in mapper.tables[0].indexes}
    
    # Check that critical fields are indexed
    indexed_fields = [
        'timestamp', 'trace_id', 'span_id', 
        'event_name', 'log_level', 'alert_level', 
        'category', 'severity', 'llm_vendor', 'detection_time'
    ]
    
    for field in indexed_fields:
        # Look for any index that includes this field
        indexed = any(field in columns for columns in indexes.values())
        assert indexed, f"Field '{field}' should be indexed in SecurityAlert model"


def test_security_alert_not_null_constraints():
    """Test that the appropriate NOT NULL constraints are defined."""
    # Get all columns with nullable info
    mapper = inspect(SecurityAlert)
    nullable_info = {column.name: column.nullable for column in mapper.columns}
    
    # Check required NOT NULL fields
    not_nullable_fields = [
        'event_id', 'schema_version', 'timestamp', 
        'alert_level', 'category', 'severity', 'description'
    ]
    
    for field in not_nullable_fields:
        assert field in nullable_info, f"Field '{field}' missing from SecurityAlert model"
        assert not nullable_info[field], f"Field '{field}' should be NOT NULL"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 