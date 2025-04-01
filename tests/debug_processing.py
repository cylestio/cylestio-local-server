#!/usr/bin/env python
"""
Debug script for processing a telemetry event.
"""
import sys
import os
import logging
from datetime import datetime, timezone
import traceback
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import get_db, init_db
from src.processing.simple_processor import SimpleProcessor

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test event data
test_event = {
    "schema_version": "1.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "trace_id": "test-trace-id",
    "span_id": "test-span-id",
    "parent_span_id": None,
    "name": "test.event",
    "level": "INFO",
    "agent_id": "test-agent",
    "attributes": {
        "test.attribute": "test-value"
    }
}

def process_event_with_debug(event_data, db_session):
    """Process an event with detailed debugging."""
    # Create session factory
    def session_factory():
        yield db_session
    
    # Create processor
    processor = SimpleProcessor(session_factory)
    
    # Process event with detailed error tracing
    try:
        # Add a hook into the _transform_event method to trace execution
        original_transform = processor._transform_event
        
        def debug_transform(self, event_data, db_session):
            """Wrapper for _transform_event with detailed debugging."""
            logger.debug(f"Starting _transform_event with data: {event_data}")
            logger.debug(f"Event timestamp type: {type(event_data['timestamp'])}")
            logger.debug(f"Event span_id type: {type(event_data.get('span_id'))}")
            logger.debug(f"Event trace_id type: {type(event_data.get('trace_id'))}")
            
            try:
                return original_transform(event_data, db_session)
            except Exception as e:
                logger.error(f"Error in _transform_event: {str(e)}")
                logger.error(traceback.format_exc())
                raise
        
        # Replace the method with our debug version
        processor._transform_event = debug_transform.__get__(processor, SimpleProcessor)
        
        # Now process the event
        logger.debug("Starting event processing")
        result = processor.process_event(event_data)
        logger.debug(f"Processing result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

def main():
    """Main function."""
    logger.info("Initializing database")
    init_db()
    
    logger.info("Creating database session")
    db = next(get_db())
    
    logger.info("Processing test event")
    logger.info(f"Test event: {test_event}")
    
    result = process_event_with_debug(test_event, db)
    
    logger.info(f"Processing result: {result}")
    
    if not result.get("success"):
        logger.error(f"Processing failed: {result.get('error')}")
        sys.exit(1)
    else:
        logger.info(f"Processing succeeded, event ID: {result.get('event_id')}")
        sys.exit(0)

if __name__ == "__main__":
    main() 