from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, String, cast
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
from dateutil.parser import parse as parse_date

from src.database.session import get_db
from src.utils.logging import get_logger
from src.models.event import Event
from src.models.trace import Trace
from src.models.span import Span
from src.models.session import Session as SessionModel
from src.models.agent import Agent

# Use the existing TelemetryEvent schema
from src.api.schemas.telemetry import TelemetryEvent

logger = get_logger(__name__)
router = APIRouter()

def parse_time_range(time_range: Optional[str], 
                   from_time: Optional[str], 
                   to_time: Optional[str]) -> tuple:
    """
    Parse time range parameters into datetime objects.
    
    Args:
        time_range: Predefined time range (1h, 1d, 7d, 30d)
        from_time: Start time in ISO 8601 format
        to_time: End time in ISO 8601 format
        
    Returns:
        tuple: (from_datetime, to_datetime)
    """
    now = datetime.utcnow()
    
    if from_time and to_time:
        # Use explicit time range if provided
        try:
            from_datetime = parse_date(from_time)
            to_datetime = parse_date(to_time)
            return from_datetime, to_datetime
        except Exception as e:
            logger.error(f"Failed to parse time range: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time format: {str(e)}"
            )
    
    # Use predefined time range if specified
    if time_range:
        to_datetime = now
        
        if time_range == "1h":
            from_datetime = now - timedelta(hours=1)
        elif time_range == "1d":
            from_datetime = now - timedelta(days=1)
        elif time_range == "7d":
            from_datetime = now - timedelta(days=7)
        elif time_range == "30d":
            from_datetime = now - timedelta(days=30)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid time_range: {time_range}. Must be one of: 1h, 1d, 7d, 30d"
            )
    else:
        # Default to last 24 hours
        to_datetime = now
        from_datetime = now - timedelta(days=1)
    
    return from_datetime, to_datetime

@router.get(
    "/telemetry/events",
    response_model=List[TelemetryEvent],
    summary="List and filter events"
)
async def list_events(
    time_range: Optional[str] = Query(None, description="Predefined time range (1h, 1d, 7d, 30d)"),
    from_time: Optional[str] = Query(None, description="Start time (ISO 8601 format)"),
    to_time: Optional[str] = Query(None, description="End time (ISO 8601 format)"),
    event_type: Optional[str] = Query(None, description="Filter by event types (comma-separated)"),
    agent_id: Optional[str] = Query(None, description="Filter by specific agent"),
    search: Optional[str] = Query(None, description="Text search across event payloads"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    db: Session = Depends(get_db)
):
    """
    List and filter events.
    
    Args:
        time_range: Predefined time range (1h, 1d, 7d, 30d)
        from_time: Start time in ISO 8601 format
        to_time: End time in ISO 8601 format
        event_type: Filter by event types (comma-separated)
        agent_id: Filter by specific agent
        search: Text search across event payloads
        limit: Maximum number of events to return
        offset: Number of events to skip
        db: Database session
        
    Returns:
        List[TelemetryEvent]: List of events
    """
    logger.info(f"Listing events with filters: time_range={time_range}, event_type={event_type}, agent_id={agent_id}")
    
    # Parse time range
    from_datetime, to_datetime = parse_time_range(time_range, from_time, to_time)
    
    # Build query
    query = db.query(Event).filter(
        Event.timestamp >= from_datetime,
        Event.timestamp <= to_datetime
    )
    
    # Apply event type filter
    if event_type:
        event_types = [et.strip() for et in event_type.split(",")]
        query = query.filter(Event.event_type.in_(event_types))
    
    # Apply agent filter
    if agent_id:
        query = query.filter(Event.agent_id == agent_id)
    
    # Apply text search if provided
    if search:
        # JSON search in PostgreSQL - adapt based on your DB
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Event.name.ilike(search_pattern),
                cast(Event.raw_data, String).ilike(search_pattern)
            )
        )
    
    # Apply pagination and ordering
    query = query.order_by(desc(Event.timestamp))
    query = query.offset(offset).limit(limit)
    
    # Execute query
    events = query.all()
    
    # Convert to response model
    result = []
    for event in events:
        # Ensure raw_data is a dict or provide an empty dict if None
        attributes = event.raw_data.get("attributes", {}) if event.raw_data else {}
        
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

@router.get(
    "/telemetry/events-timeline",
    response_model=Dict[str, Any],
    summary="Get event timeline distribution"
)
async def get_event_timeline(
    time_range: Optional[str] = Query(None, description="Predefined time range (1h, 1d, 7d, 30d)"),
    from_time: Optional[str] = Query(None, description="Start time (ISO 8601 format)"),
    to_time: Optional[str] = Query(None, description="End time (ISO 8601 format)"),
    event_type: Optional[str] = Query(None, description="Filter by event types (comma-separated)"),
    agent_id: Optional[str] = Query(None, description="Filter by specific agent"),
    interval: str = Query("1h", description="Time interval (1m, 5m, 1h, 1d)"),
    db: Session = Depends(get_db)
):
    """
    Get event distribution over time with specified interval.
    
    Args:
        time_range: Predefined time range (1h, 1d, 7d, 30d)
        from_time: Start time in ISO 8601 format
        to_time: End time in ISO 8601 format
        event_type: Filter by event types (comma-separated)
        agent_id: Filter by specific agent
        interval: Time interval (1m, 5m, 1h, 1d)
        db: Database session
        
    Returns:
        Dict: Event timeline distribution data
    """
    logger.info(f"Getting event timeline with interval {interval}")
    
    # Parse time range
    from_datetime, to_datetime = parse_time_range(time_range, from_time, to_time)
    
    # Determine interval in seconds
    if interval == "1m":
        interval_seconds = 60
    elif interval == "5m":
        interval_seconds = 300
    elif interval == "1h":
        interval_seconds = 3600
    elif interval == "1d":
        interval_seconds = 86400
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interval: {interval}. Must be one of: 1m, 5m, 1h, 1d"
        )
    
    # Create time buckets
    timeline_data = []
    current_time = from_datetime
    
    while current_time <= to_datetime:
        next_time = current_time + timedelta(seconds=interval_seconds)
        
        # Query for events in this time bucket
        query = db.query(
            func.count(Event.id).label("total"),
            func.count(Event.id).filter(Event.event_type == "llm").label("llm"),
            func.count(Event.id).filter(Event.event_type == "tool").label("tool"),
            func.count(Event.id).filter(Event.event_type == "security").label("security"),
            func.count(Event.id).filter(Event.event_type == "framework").label("framework"),
            func.count(Event.id).filter(Event.level.ilike("error%")).label("error"),
            func.count(Event.id).filter(Event.level.ilike("warn%")).label("warning"),
            func.count(Event.id).filter(Event.level.ilike("info%")).label("info")
        ).filter(
            Event.timestamp >= current_time,
            Event.timestamp < next_time
        )
        
        # Apply agent filter
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        # Apply event type filter
        if event_type:
            event_types = [et.strip() for et in event_type.split(",")]
            query = query.filter(Event.event_type.in_(event_types))
        
        # Execute query
        result = query.first()
        
        # Add to timeline data
        if result:
            timeline_data.append({
                "timestamp": current_time.isoformat(),
                "total": result.total,
                "by_type": {
                    "llm": result.llm,
                    "tool": result.tool,
                    "security": result.security,
                    "framework": result.framework
                },
                "by_status": {
                    "success": result.total - (result.error + result.warning),
                    "error": result.error,
                    "warning": result.warning
                }
            })
        else:
            timeline_data.append({
                "timestamp": current_time.isoformat(),
                "total": 0,
                "by_type": {
                    "llm": 0,
                    "tool": 0,
                    "security": 0,
                    "framework": 0
                },
                "by_status": {
                    "success": 0,
                    "error": 0,
                    "warning": 0
                }
            })
        
        # Move to next interval
        current_time = next_time
    
    # Build response
    time_period = time_range if time_range else f"Custom ({from_datetime.isoformat()} to {to_datetime.isoformat()})"
    
    return {
        "intervals": timeline_data,
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "time_period": time_period,
            "interval": interval,
            "filters_applied": {
                "time_range": time_range,
                "from_time": from_time,
                "to_time": to_time,
                "event_type": event_type,
                "agent_id": agent_id
            }
        }
    }

@router.get(
    "/telemetry/events/{event_id}",
    response_model=TelemetryEvent,
    summary="Get event details"
)
async def get_event_details(
    event_id: str = Path(..., description="Event ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific event.
    
    Args:
        event_id: Event ID
        db: Database session
        
    Returns:
        TelemetryEvent: Detailed event information
    """
    logger.info(f"Getting details for event {event_id}")
    
    # Get the event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    # Convert to response model
    # Ensure raw_data is a dict or provide an empty dict if None
    attributes = event.raw_data.get("attributes", {}) if event.raw_data else {}
    
    # Add related events as attributes if available
    if event.span_id:
        related_events_query = db.query(Event).filter(
            Event.span_id == event.span_id,
            Event.id != event.id
        ).order_by(Event.timestamp).all()
        
        if related_events_query:
            related_event_ids = [str(e.id) for e in related_events_query]
            attributes["related_events"] = related_event_ids
    
    # Include specialized data in attributes if available
    specialized_event = event.specialized_event
    if specialized_event:
        if event.event_type == "llm":
            attributes.update({
                "llm.model": specialized_event.model,
                "llm.duration_ms": specialized_event.duration_ms,
                "llm.prompt": specialized_event.prompt,
                "llm.completion": specialized_event.completion
            })
        elif event.event_type == "tool":
            attributes.update({
                "tool.name": specialized_event.tool_name,
                "tool.category": specialized_event.category,
                "tool.duration_ms": specialized_event.duration_ms,
                "tool.input": specialized_event.input_data,
                "tool.output": specialized_event.output_data
            })
    
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
    "/telemetry/sessions/{session_id}/events",
    response_model=List[TelemetryEvent],
    summary="Get events by session ID"
)
async def get_session_events(
    session_id: str = Path(..., description="Session ID"),
    db: Session = Depends(get_db)
):
    """
    Get all events that belong to a specific session.
    
    Args:
        session_id: ID of the session
        
    Returns:
        List[TelemetryEvent]: List of events in the session
    """
    logger.info(f"Retrieving events for session: {session_id}")
    
    events = db.query(Event).filter(Event.session_id == session_id).order_by(Event.timestamp).all()
    
    # Convert to response model
    result = []
    for event in events:
        # Ensure raw_data is a dict or provide an empty dict if None
        attributes = event.raw_data.get("attributes", {}) if event.raw_data else {}
        
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