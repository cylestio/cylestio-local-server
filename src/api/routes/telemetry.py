from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from src.database.session import get_db
from src.utils.logging import get_logger
from src.api.schemas.telemetry import (
    TelemetryEventCreate, 
    TelemetryEventBatchCreate,
    TelemetryEvent,
    TelemetryEventResponse,
    TelemetryEventBatchResponse
)
from src.processing.simple_processor import SimpleProcessor
from src.models.event import Event

logger = get_logger(__name__)
router = APIRouter()

def process_event(event_data: Dict[str, Any], db: Session) -> Event:
    """
    Process a telemetry event using the SimpleProcessor.
    
    Args:
        event_data: The event data to process
        db: Database session
        
    Returns:
        Event: The processed event
    """
    # Create a processor - session factory that returns a list containing the session
    # We create it as a function that returns an iterator to match SimpleProcessor's expectations
    def session_factory():
        yield db
    
    # Create a processor
    processor = SimpleProcessor(session_factory)
    
    # Process the event
    result = processor.process_event(event_data)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        raise ValueError(f"Failed to process event: {error_msg}")
    
    # Get the event from the database
    event_id = result.get("event_id")
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise ValueError(f"Event created but not found in database: {event_id}")
        
    return event

@router.post(
    "/telemetry", 
    response_model=TelemetryEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a single telemetry event"
)
async def create_telemetry_event(
    event: TelemetryEventCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit a single telemetry event for processing and storage.
    
    Args:
        event: The telemetry event data
        
    Returns:
        TelemetryEventResponse: Response with event processing result
    """
    logger.info(f"Processing telemetry event: {event.name}")
    
    try:
        # Convert Pydantic model to dict for processing
        event_dict = event.dict()
        
        # Process the event
        processed_event = process_event(event_dict, db)
        
        # Return response
        return TelemetryEventResponse(
            success=True,
            event_id=str(processed_event.id)
        )
        
    except ValueError as e:
        logger.error(f"Error processing telemetry event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error processing telemetry event: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "error": "Internal server error processing telemetry event"}
        )

@router.post(
    "/telemetry/batch", 
    response_model=TelemetryEventBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit multiple telemetry events in batch"
)
async def create_telemetry_events_batch(
    batch: TelemetryEventBatchCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit multiple telemetry events for processing and storage.
    
    Args:
        batch: Batch of telemetry events
        
    Returns:
        TelemetryEventBatchResponse: Response with batch processing results
    """
    logger.info(f"Processing telemetry batch with {len(batch.events)} events")
    
    try:
        processed = 0
        failed = 0
        details = []
        
        for idx, event in enumerate(batch.events):
            try:
                # Convert Pydantic model to dict for processing
                event_dict = event.dict()
                
                # Process the event
                processed_event = process_event(event_dict, db)
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing event {idx} in batch: {str(e)}")
                failed += 1
                details.append({
                    "index": idx,
                    "error": str(e),
                    "event_name": event.name
                })
        
        # Return batch processing results
        return TelemetryEventBatchResponse(
            success=failed == 0,
            total=len(batch.events),
            processed=processed,
            failed=failed,
            details=details if failed > 0 else None
        )
    except Exception as e:
        logger.error(f"Error processing telemetry batch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "error": "Internal server error processing telemetry batch"}
        )

@router.get(
    "/telemetry/events", 
    response_model=List[TelemetryEvent],
    summary="Get telemetry events"
)
async def get_telemetry_events(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    event_name: Optional[str] = Query(None, description="Filter by event name"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    from_time: Optional[datetime] = Query(None, description="Start time"),
    to_time: Optional[datetime] = Query(None, description="End time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    db: Session = Depends(get_db)
):
    """
    Get telemetry events with optional filtering.
    
    Args:
        agent_id: Filter by agent ID
        event_name: Filter by event name
        level: Filter by log level
        trace_id: Filter by trace ID
        from_time: Filter by start time
        to_time: Filter by end time
        limit: Maximum number of events to return
        offset: Number of events to skip
        
    Returns:
        List[TelemetryEvent]: List of matching telemetry events
    """
    logger.info(f"Querying telemetry events with filters: agent_id={agent_id}, name={event_name}, level={level}")
    
    # Build query
    query = db.query(Event)
    
    # Apply filters
    if agent_id:
        query = query.filter(Event.agent_id == agent_id)
    if event_name:
        query = query.filter(Event.name == event_name)
    if level:
        query = query.filter(Event.level == level)
    if trace_id:
        query = query.filter(Event.trace_id == trace_id)
    if from_time:
        query = query.filter(Event.timestamp >= from_time)
    if to_time:
        query = query.filter(Event.timestamp <= to_time)
    
    # Apply pagination
    query = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit)
    
    # Execute query
    events = query.all()
    
    # Convert to response model
    result = []
    for event in events:
        # Ensure raw_data is a dict or provide an empty dict if None
        attributes = event.raw_data if event.raw_data is not None else {}
        
        event_dict = {
            "id": str(event.id),  # Convert ID to string
            "schema_version": event.schema_version,
            "timestamp": event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp,  # Convert datetime to ISO string
            "trace_id": event.trace_id,
            "span_id": event.span_id,
            "parent_span_id": event.parent_span_id,
            "name": event.name,
            "level": event.level,
            "agent_id": event.agent_id,
            "attributes": attributes
        }
        result.append(TelemetryEvent(**event_dict))
    
    return result

@router.get(
    "/telemetry/events/{event_id}", 
    response_model=TelemetryEvent,
    summary="Get a specific telemetry event by ID"
)
async def get_telemetry_event(
    event_id: str = Path(..., description="Event ID"),
    db: Session = Depends(get_db)
):
    """
    Get a specific telemetry event by ID.
    
    Args:
        event_id: ID of the event to retrieve
        
    Returns:
        TelemetryEvent: The telemetry event
        
    Raises:
        HTTPException: If the event is not found
    """
    logger.info(f"Retrieving telemetry event with ID: {event_id}")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        logger.warning(f"Event not found: {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    # Convert to response model
    # Ensure raw_data is a dict or provide an empty dict if None
    attributes = event.raw_data if event.raw_data is not None else {}
    
    event_dict = {
        "id": str(event.id),
        "schema_version": event.schema_version,
        "timestamp": event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp,
        "trace_id": event.trace_id,
        "span_id": event.span_id,
        "parent_span_id": event.parent_span_id,
        "name": event.name,
        "level": event.level,
        "agent_id": event.agent_id,
        "attributes": attributes
    }
    
    return TelemetryEvent(**event_dict)

@router.get(
    "/telemetry/traces/{trace_id}",
    response_model=List[TelemetryEvent],
    summary="Get all events in a trace"
)
async def get_trace_events(
    trace_id: str = Path(..., description="Trace ID"),
    db: Session = Depends(get_db)
):
    """
    Get all events that belong to a specific trace.
    
    Args:
        trace_id: ID of the trace
        
    Returns:
        List[TelemetryEvent]: List of events in the trace
    """
    logger.info(f"Retrieving events for trace: {trace_id}")
    
    events = db.query(Event).filter(Event.trace_id == trace_id).order_by(Event.timestamp).all()
    
    # Convert to response model
    result = []
    for event in events:
        # Ensure raw_data is a dict or provide an empty dict if None
        attributes = event.raw_data if event.raw_data is not None else {}
        
        event_dict = {
            "id": str(event.id),
            "schema_version": event.schema_version,
            "timestamp": event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp,
            "trace_id": event.trace_id,
            "span_id": event.span_id,
            "parent_span_id": event.parent_span_id,
            "name": event.name,
            "level": event.level,
            "agent_id": event.agent_id,
            "attributes": attributes
        }
        result.append(TelemetryEvent(**event_dict))
    
    return result 