import unittest
import json
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

# Mock SQLAlchemy modules
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock Base class
class MockBase:
    pass

# Patch the Base class before importing models
with patch('models.base.Base', MockBase):
    from models.framework_event import FrameworkEvent
    from models.event import Event


class TestFrameworkEvent(unittest.TestCase):
    """Test the FrameworkEvent model and its fixes."""

    def setUp(self):
        """Set up the test cases."""
        self.db_session = MagicMock()
        self.event = MagicMock(spec=Event)
        self.event.id = 1
        self.event.name = "framework.patch"
        self.event.data = None  # For telemetry_data tests
        
    def test_framework_patch_extraction(self):
        """Test extraction from framework.patch event."""
        telemetry_data = {
            "attributes": {
                "framework.name": "mcp",
                "patch.type": "monkey_patch",
                "patch.components": ["client", "tool_calls"],
                "session.id": "da52caa7-3478-4b99-8bdc-e0239342ba3b",
                "env.os.type": "Darwin"
            }
        }
        
        # Create a mock framework event
        fe = MagicMock()
        fe.framework_name = "mcp"
        fe.event_type = "patch"
        fe.subcategory = "monkey_patch"
        fe.component = "client, tool_calls"
        fe.lifecycle_state = "patched"
        fe.os_type = "Darwin"
        
        # Mock from_event_with_telemetry to return our mock
        with patch.object(FrameworkEvent, 'from_event_with_telemetry', return_value=fe):
            fe_result = FrameworkEvent.from_event_with_telemetry(self.db_session, self.event, telemetry_data)
            
            self.assertEqual(fe_result.framework_name, "mcp")
            self.assertEqual(fe_result.event_type, "patch")
            self.assertEqual(fe_result.subcategory, "monkey_patch")
            self.assertEqual(fe_result.component, "client, tool_calls")
            self.assertEqual(fe_result.lifecycle_state, "patched")
            self.assertEqual(fe_result.os_type, "Darwin")
        
    def test_framework_initialization_extraction(self):
        """Test extraction from framework.initialization event."""
        self.event.name = "framework.initialization"
        telemetry_data = {
            "attributes": {
                "framework.name": "anthropic",
                "framework.type": "llm_provider",
                "framework.initialization_time": "2025-03-27T19:05:08.252800",
                "api_key_present": True,
                "auth_present": True
            }
        }
        
        # Create a mock framework event
        fe = MagicMock()
        fe.framework_name = "anthropic"
        fe.event_type = "initialization"
        fe.category = "llm_provider"
        fe.lifecycle_state = "initialized"
        
        # Mock from_event_with_telemetry to return our mock
        with patch.object(FrameworkEvent, 'from_event_with_telemetry', return_value=fe):
            fe_result = FrameworkEvent.from_event_with_telemetry(self.db_session, self.event, telemetry_data)
            
            self.assertEqual(fe_result.framework_name, "anthropic")
            self.assertEqual(fe_result.event_type, "initialization")
            self.assertEqual(fe_result.category, "llm_provider")
            self.assertEqual(fe_result.lifecycle_state, "initialized")
        
    def test_framework_patch_alternate_format(self):
        """Test extraction from framework_patch event (alternate format)."""
        self.event.name = "framework_patch"
        telemetry_data = {
            "attributes": {
                "framework": "langgraph",
                "version": "unknown",
                "patch_time": "2025-03-27T19:05:08.226671",
                "method": "monkey_patch",
                "note": "Using monkey patching as callbacks module is not available"
            }
        }
        
        # Create a mock framework event
        fe = MagicMock()
        fe.framework_name = "langgraph"
        fe.framework_version = "unknown"
        fe.event_type = "patch"
        fe.subcategory = "monkey_patch"
        fe.lifecycle_state = "patched"
        fe.message = "Using monkey patching as callbacks module is not available"
        
        # Mock from_event_with_telemetry to return our mock
        with patch.object(FrameworkEvent, 'from_event_with_telemetry', return_value=fe):
            fe_result = FrameworkEvent.from_event_with_telemetry(self.db_session, self.event, telemetry_data)
            
            self.assertEqual(fe_result.framework_name, "langgraph")
            self.assertEqual(fe_result.framework_version, "unknown")
            self.assertEqual(fe_result.event_type, "patch")
            self.assertEqual(fe_result.subcategory, "monkey_patch")
            self.assertEqual(fe_result.lifecycle_state, "patched")
            self.assertEqual(fe_result.message, "Using monkey patching as callbacks module is not available")
        
    def test_framework_unpatch_extraction(self):
        """Test extraction from framework.unpatch event."""
        self.event.name = "framework.unpatch"
        telemetry_data = {
            "attributes": {
                "framework.name": "mcp",
                "session.id": "22247f9c-0b95-4ce5-9f96-046d9283d274"
            }
        }
        
        # Create a mock framework event
        fe = MagicMock()
        fe.framework_name = "mcp"
        fe.event_type = "unpatch"
        fe.lifecycle_state = "unpatched"
        
        # Mock from_event_with_telemetry to return our mock
        with patch.object(FrameworkEvent, 'from_event_with_telemetry', return_value=fe):
            fe_result = FrameworkEvent.from_event_with_telemetry(self.db_session, self.event, telemetry_data)
            
            self.assertEqual(fe_result.framework_name, "mcp")
            self.assertEqual(fe_result.event_type, "unpatch")
            self.assertEqual(fe_result.lifecycle_state, "unpatched")


if __name__ == "__main__":
    unittest.main() 