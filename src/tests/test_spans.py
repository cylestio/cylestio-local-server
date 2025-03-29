#!/usr/bin/env python3
"""
Test script to validate the enhanced span implementation.
"""
import sys
import os
from datetime import datetime, timedelta
import unittest
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import init_db, create_all, get_db
from models.span import Span
from models.trace import Trace
from models.agent import Agent
from models.event import Event
from processing.simple_processor import SimpleProcessor

class SpanTest(unittest.TestCase):
    """Test case for span functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # In-memory SQLite database
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        create_all()
        
        # Get a session
        self.db_session = next(get_db())
        
        # Create a test agent
        self.agent = Agent(
            agent_id="test-agent",
            name="Test Agent",
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            is_active=True
        )
        self.db_session.add(self.agent)
        
        # Create a test trace
        self.trace = Trace(
            trace_id="test-trace-id",
            agent_id="test-agent"
        )
        self.db_session.add(self.trace)
        self.db_session.commit()
        
        # Initialize processor
        self.processor = SimpleProcessor(get_db)
    
    def tearDown(self):
        """Clean up resources."""
        self.db_session.close()
    
    def test_span_creation(self):
        """Test basic span creation."""
        # Create a span
        span = Span.get_or_create(
            self.db_session,
            span_id="test-span-1",
            trace_id="test-trace-id",
            event_name="llm.call.start"
        )
        
        self.assertEqual(span.span_id, "test-span-1")
        self.assertEqual(span.trace_id, "test-trace-id")
        self.assertEqual(span.name, "llm_interaction")
        self.assertIsNotNone(span.start_timestamp)
        self.assertIsNone(span.end_timestamp)
        self.assertIsNone(span.parent_span_id)
        self.assertEqual(span.root_span_id, "test-span-1")  # It's its own root
    
    def test_span_hierarchy(self):
        """Test parent-child span relationships."""
        # Create parent span
        parent_span = Span.get_or_create(
            self.db_session,
            span_id="parent-span",
            trace_id="test-trace-id",
            event_name="llm.request"
        )
        # Commit to database to ensure it's saved
        self.db_session.commit()
        
        # Create child span
        child_span = Span.get_or_create(
            self.db_session,
            span_id="child-span",
            trace_id="test-trace-id",
            parent_span_id="parent-span",
            event_name="llm.call.start"
        )
        # Commit to database to ensure it's saved
        self.db_session.commit()
        
        # Test relationships
        self.assertEqual(child_span.parent_span_id, "parent-span")
        self.assertEqual(child_span.root_span_id, "parent-span")
        
        # Reload from database to ensure relationship is persisted
        child_span = self.db_session.query(Span).filter_by(span_id="child-span").first()
        parent_span = self.db_session.query(Span).filter_by(span_id="parent-span").first()
        
        # Test getting children
        children = parent_span.get_child_spans(self.db_session)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].span_id, "child-span")
        
        # Test span tree
        tree = parent_span.get_span_tree(self.db_session)
        self.assertEqual(len(tree), 2)
        span_ids = {span.span_id for span in tree}
        self.assertEqual(span_ids, {"parent-span", "child-span"})
    
    def test_name_derivation(self):
        """Test span name derivation from event names."""
        test_cases = [
            ("llm.call.start", "llm_interaction"),
            ("llm.call.finish", "llm_interaction"),
            ("tool.call.start", "tool_interaction"),
            ("framework.initialization", "framework_initialization"),
            ("security.content.suspicious", "security_content.suspicious"),
            ("monitoring.start", "monitoring_start"),
            ("unknown", "unknown")
        ]
        
        for event_name, expected_name in test_cases:
            derived_name = Span._derive_span_name_from_event(event_name)
            self.assertEqual(derived_name, expected_name)
    
    def test_span_timestamps(self):
        """Test span timestamp updates."""
        # Create a span
        span = Span.get_or_create(
            self.db_session,
            span_id="timestamp-span",
            trace_id="test-trace-id"
        )
        
        # Create events with different timestamps
        now = datetime.now()
        start_time = now - timedelta(minutes=5)
        middle_time = now
        end_time = now + timedelta(minutes=5)
        
        # Create start event
        start_event = Event(
            name="test.start",
            timestamp=start_time,
            level="INFO",
            agent_id="test-agent",
            trace_id="test-trace-id",
            span_id="timestamp-span",
            schema_version="1.0",
            event_type="test"
        )
        self.db_session.add(start_event)
        
        # Create middle event
        middle_event = Event(
            name="test.progress",
            timestamp=middle_time,
            level="INFO",
            agent_id="test-agent",
            trace_id="test-trace-id",
            span_id="timestamp-span",
            schema_version="1.0",
            event_type="test"
        )
        self.db_session.add(middle_event)
        
        # Create end event
        end_event = Event(
            name="test.finish",
            timestamp=end_time,
            level="INFO",
            agent_id="test-agent",
            trace_id="test-trace-id",
            span_id="timestamp-span",
            schema_version="1.0",
            event_type="test"
        )
        self.db_session.add(end_event)
        self.db_session.commit()
        
        # Update span timestamps from events
        span.update_timestamps_from_events(self.db_session)
        
        # Verify timestamps
        self.assertEqual(span.start_timestamp, start_time)
        self.assertEqual(span.end_timestamp, end_time)
        
        # Test duration calculation
        duration = span.get_duration_seconds()
        expected_duration = (end_time - start_time).total_seconds()
        self.assertEqual(duration, expected_duration)
    
    def test_process_example_events(self):
        """Test processing example events with spans."""
        # Load a few example records with spans
        example_file = Path(__file__).parent.parent.parent / "example_records.json"
        
        # Check if file exists
        if not example_file.exists():
            self.skipTest(f"Example records file not found: {example_file}")
        
        # Load events with spans
        events_with_spans = []
        span_ids = set()
        with open(example_file, 'r') as f:
            for line in f:
                try:
                    event_data = json.loads(line)
                    if event_data.get("span_id"):
                        events_with_spans.append(event_data)
                        span_ids.add(event_data["span_id"])
                except json.JSONDecodeError:
                    continue
                
                # Limit to 10 events for testing
                if len(events_with_spans) >= 10:
                    break
        
        # Skip if no events with spans found
        if not events_with_spans:
            self.skipTest("No events with spans found in example records")
        
        # Process events
        for event_data in events_with_spans:
            result = self.processor.process_event(event_data)
            self.assertTrue(result["success"], f"Failed to process event: {result.get('error')}")
        
        # Check that spans were created
        for span_id in span_ids:
            span = self.db_session.query(Span).filter_by(span_id=span_id).first()
            self.assertIsNotNone(span, f"Span {span_id} was not created")
            self.assertIsNotNone(span.name, f"Span {span_id} name is None")
            self.assertIsNotNone(span.start_timestamp, f"Span {span_id} start_timestamp is None")

if __name__ == "__main__":
    unittest.main() 