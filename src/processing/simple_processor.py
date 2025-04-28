"""
Simple processor for telemetry events.

This module provides a simple processor for validating and storing telemetry
events in the database.
"""
import json
import logging
import traceback
from typing import Dict, Any, List, Union, Optional, Tuple
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.event import Event
from src.models.agent import Agent
from src.models.trace import Trace
from src.models.span import Span
from src.models.llm_interaction import LLMInteraction
from src.models.security_alert import SecurityAlert, SecurityAlertTrigger
from src.models.framework_event import FrameworkEvent
from src.models.session import Session as SessionModel
from src.models.tool_interaction import ToolInteraction

# Import our custom JSON encoder
from src.utils.json_serializer import dumps, loads

# Set up logger
logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Base exception for processing errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class SimpleProcessor:
    """
    Simple processor for telemetry events.
    
    This class provides a straightforward way to process telemetry events,
    validating them and storing them in the database.
    """
    
    def __init__(self, db_session_factory):
        """Initialize the processor with a session factory."""
        self.db_session_factory = db_session_factory
    
    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single event by validating, transforming, and storing it.
        
        Args:
            event_data: Dictionary containing the event data
            
        Returns:
            Dict with processing results
        """
        logger.debug(f"Processing event: {event_data.get('name', 'Unknown')}")
        
        # Validate the event data
        validation_result = self._validate_event(event_data)
        if not validation_result.get("valid", False):
            logger.warning(f"Event validation failed: {validation_result.get('error')}")
            return {
                "success": False,
                "error": validation_result.get("error", "Event validation failed")
            }
        
        # Get database session from generator
        db_session = None
        try:
            db_session = next(self.db_session_factory())
            
            # Check if all required tables exist (sanity check)
            if not self._check_tables_exist(db_session):
                logger.error("Database tables are not properly initialized")
                return {
                    "success": False,
                    "error": "Database tables are not properly initialized"
                }
            
            # Ensure agent exists for this event (create if not exists)
            agent_id = event_data.get("agent_id")
            self._ensure_agent_exists(db_session, agent_id)
            
            # Transform event data into database models
            event, related_models = self._transform_event(event_data, db_session)
            
            # Add all models to session
            for model in related_models:
                db_session.add(model)
            
            # Commit the changes
            db_session.commit()
            
            logger.info(f"Successfully processed event: {event_data.get('name')} (ID: {event.id})")
            return {
                "success": True,
                "event_id": event.id,
                "message": f"Event {event.id} processed successfully"
            }
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            logger.exception(e)
            if db_session:
                db_session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if db_session:
                db_session.close()
    
    def process_json_event(self, json_data: str) -> Dict[str, Any]:
        """
        Process a single event from a JSON string.
        
        Args:
            json_data: JSON string containing the event data
            
        Returns:
            Dict[str, Any]: Process result
        """
        try:
            # Parse JSON data
            event_data = loads(json_data)
            
            # Process the event
            return self.process_event(event_data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ProcessingError(f"Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing JSON event: {str(e)}")
            raise ProcessingError(f"Processing error: {str(e)}")
    
    def process_batch(self, events_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of events.
        
        Args:
            events_data: List of event data dictionaries
            
        Returns:
            Dict with batch processing results
        """
        results = []
        
        # Create one database session for the entire batch
        db_session = next(self.db_session_factory())
        
        try:
            for event_data in events_data:
                # Validate the event data
                validation_result = self._validate_event(event_data)
                if not validation_result["valid"]:
                    results.append({
                        "success": False, 
                        "error": validation_result["error"],
                        "details": validation_result.get("details", {})
                    })
                    continue
                
                try:
                    # Process the event
                    event, related_models = self._transform_event(event_data, db_session)
                    
                    # Add to session
                    db_session.add(event)
                    for model in related_models:
                        db_session.add(model)
                    
                    results.append({
                        "success": True,
                        "event_id": event.id,
                        "event_name": event.name
                    })
                except Exception as e:
                    logger.error(f"Error processing event in batch: {str(e)}", exc_info=True)
                    results.append({
                        "success": False,
                        "error": str(e),
                        "details": {"exception_type": e.__class__.__name__}
                    })
            
            # Commit all changes at once
            db_session.commit()
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error processing batch: {str(e)}", exc_info=True)
            
            # Add failed result for all events that didn't have a result yet
            while len(results) < len(events_data):
                results.append({
                    "success": False,
                    "error": f"Batch processing error: {str(e)}",
                    "details": {"exception_type": e.__class__.__name__}
                })
        
        finally:
            db_session.close()
        
        return {
            "total": len(events_data),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results
        }
    
    def process_json_batch(self, json_data: str) -> Dict[str, Any]:
        """
        Process a batch of events from a JSON string.
        
        Args:
            json_data: JSON string containing an array of event data
            
        Returns:
            Dict[str, Any]: Process result
        """
        try:
            # Parse JSON data
            events_data = loads(json_data)
            
            # Check if the data is a list
            if not isinstance(events_data, list):
                # Handle case where a single event is provided instead of an array
                return self.process_event(events_data)
            
            # Process the batch
            return self.process_batch(events_data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise ProcessingError(f"Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing JSON batch: {str(e)}")
            raise ProcessingError(f"Batch processing error: {str(e)}")
    
    def _validate_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate event data.
        
        Args:
            event_data: Dictionary containing the event data
            
        Returns:
            Dict with validation results
        """
        # Check required fields
        required_fields = ["timestamp", "name", "level", "agent_id"]
        for field in required_fields:
            if field not in event_data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }
        
        # Basic type validation
        if not isinstance(event_data["timestamp"], str):
            return {
                "valid": False,
                "error": f"Field timestamp must be a string, got {type(event_data['timestamp']).__name__}"
            }
            
        # Validate timestamp format
        try:
            # Convert to datetime object - strip timezone info to make it naive
            timestamp = datetime.fromisoformat(event_data["timestamp"].replace('Z', '+00:00'))
            # Replace the string timestamp with a naive datetime to avoid timezone comparison issues
            event_data["timestamp"] = timestamp.replace(tzinfo=None)
        except ValueError:
            return {
                "valid": False,
                "error": f"Invalid timestamp format: {event_data['timestamp']}"
            }
        
        if not isinstance(event_data["name"], str):
            return {
                "valid": False,
                "error": f"Field name must be a string, got {type(event_data['name']).__name__}"
            }
        
        if not isinstance(event_data["level"], str):
            return {
                "valid": False,
                "error": f"Field level must be a string, got {type(event_data['level']).__name__}"
            }
        
        if not isinstance(event_data["agent_id"], str):
            return {
                "valid": False,
                "error": f"Field agent_id must be a string, got {type(event_data['agent_id']).__name__}"
            }
        
        # Validate schema version if present
        if "schema_version" in event_data:
            if event_data["schema_version"] != "1.0":
                return {
                    "valid": False,
                    "error": f"Unsupported schema version: {event_data['schema_version']}"
                }
        
        # All validations passed
        return {"valid": True}
    
    def _transform_event(self, event_data: Dict[str, Any], db_session: Session) -> Tuple[Event, List[Any]]:
        """
        Transform event data into database models.
        
        Args:
            event_data: Dictionary containing the event data
            db_session: SQLAlchemy session
            
        Returns:
            Tuple of (event, related_models)
        """
        related_models = []
        
        # Find or create agent
        agent = db_session.query(Agent).filter_by(agent_id=event_data["agent_id"]).first()
        if not agent:
            current_time = datetime.utcnow()
            agent = Agent(
                agent_id=event_data["agent_id"],
                name=f"Agent-{event_data['agent_id'][:8]}",
                first_seen=current_time,
                last_seen=current_time,
                is_active=True
            )
            related_models.append(agent)
        
        # Handle trace if present
        trace = None
        if "trace_id" in event_data:
            trace = db_session.query(Trace).filter_by(trace_id=event_data["trace_id"]).first()
            if not trace:
                trace = Trace(
                    trace_id=event_data["trace_id"],
                    agent_id=event_data["agent_id"]
                )
                if agent:
                    trace.agent = agent
                related_models.append(trace)
        
        # Parse event timestamp
        if isinstance(event_data["timestamp"], str):
            timestamp_dt = datetime.fromisoformat(event_data["timestamp"].replace('Z', '+00:00'))
        else:
            # Already a datetime object
            timestamp_dt = event_data["timestamp"]
        
        # Handle span if present
        span = None
        if "span_id" in event_data and event_data["span_id"]:
            # Use the enhanced Span.get_or_create method
            span = Span.get_or_create(
                db_session,
                span_id=event_data["span_id"],
                trace_id=event_data.get("trace_id"),
                parent_span_id=event_data.get("parent_span_id"),
                # Try to derive span name from event name
                event_name=event_data.get("name")
            )
            
            # Update span timestamps with the event timestamp
            span.update_timestamps(db_session, timestamp_dt, timestamp_dt)
            
            if trace:
                span.trace = trace
            
            # Check if this is a span-closing event
            event_name = event_data.get("name", "")
            if event_name.endswith(".finish") or event_name.endswith(".end") or event_name.endswith(".stop"):
                # This is likely a closing event, so update the end timestamp
                span.update_timestamps(db_session, end_time=timestamp_dt)
            elif event_name.endswith(".start") or event_name.endswith(".begin"):
                # This is likely an opening event, ensure start timestamp is set
                span.update_timestamps(db_session, start_time=timestamp_dt)
            
            # Always add span to related_models
            if span not in related_models:
                related_models.append(span)
        
        # Determine event type based on name
        event_name = event_data["name"]
        if event_name.startswith("llm."):
            event_type = "llm"
        elif event_name.startswith("security."):
            event_type = "security"
        elif event_name.startswith("framework."):
            event_type = "framework"
        elif event_name.startswith("tool."):
            event_type = "tool"
        else:
            event_type = "generic"
        
        # Create base event
        event = Event(
            name=event_data["name"],
            timestamp=timestamp_dt,
            level=event_data["level"],
            agent_id=event_data["agent_id"],
            trace_id=event_data.get("trace_id"),
            span_id=event_data.get("span_id"),
            parent_span_id=event_data.get("parent_span_id"),
            schema_version=event_data.get("schema_version", "1.0"),
            event_type=event_type,
            raw_data=event_data  # Store the entire event data in raw_data
        )
        
        # Set relationships
        event.agent = agent
        if trace:
            event.trace = trace
        if span:
            event.span = span
            
        # Add and flush the event to get an ID
        db_session.add(event)
        db_session.flush()
        
        # Create specialized event if needed
        specialized_event = None
        
        if event_type == "llm":
            logger.debug(f"Creating LLM interaction for event {event.id}, name: {event.name}")
            logger.debug(f"Event data keys: {list(event_data.keys())}")
            logger.debug(f"Attributes: {event_data.get('attributes', {})}")
            
            try:
                specialized_event = LLMInteraction.from_event(db_session, event, event_data)
                if specialized_event:
                    logger.debug(f"Created LLM interaction with ID {specialized_event.id}")
                else:
                    logger.warning(f"Failed to create LLM interaction for event {event.id}")
            except Exception as e:
                logger.error(f"Exception creating LLM interaction: {str(e)}")
                logger.exception(e)
        elif event_type == "security":
            # Use the new telemetry method for processing security events
            try:
                from src.services.security_event_processor import process_security_event
                # The event has already been created, so we just need to create the security alert
                specialized_event = SecurityAlert.from_telemetry_event(db_session, event, event_data)
                if specialized_event:
                    logger.debug(f"Created Security Alert with ID {specialized_event.id}")
                else:
                    logger.warning(f"Failed to create Security Alert for event {event.id}")
            except Exception as e:
                logger.error(f"Exception creating Security Alert: {str(e)}")
                logger.exception(e)
                # Fall back to the old method if the new one fails
                specialized_event = SecurityAlert.from_event(db_session, event, event_data)
        elif event_type == "framework":
            specialized_event = FrameworkEvent.from_event(db_session, event, event_data)
        elif event_type == "tool":
            try:
                # Import here to avoid circular imports
                from src.models.tool_interaction import ToolInteraction
                specialized_event = ToolInteraction.from_event(db_session, event, event_data)
                if specialized_event:
                    logger.debug(f"Created Tool interaction with ID {specialized_event.id}")
                else:
                    logger.warning(f"Failed to create Tool interaction for event {event.id}")
            except Exception as e:
                logger.error(f"Exception creating Tool interaction: {str(e)}")
                logger.exception(e)
        
        if specialized_event:
            related_models.append(specialized_event)
            # Flush to ensure specialized event has an ID
            db_session.flush()
        
        # Process attributes
        if "attributes" in event_data and event_data["attributes"]:
            self._process_attributes(event, event_data["attributes"], event_type, related_models, db_session)
        
        # Check if this event could be a trigger for any existing security alerts
        if "span_id" in event_data and event_data["span_id"] and event_type != "security":
            self._check_event_as_security_trigger(event, db_session)
        
        return event, related_models
    
    def _process_attributes(
        self, 
        event: Event, 
        attributes: Dict[str, Any], 
        event_type: str,
        related_models: List[Any],
        db_session: Session
    ) -> None:
        """
        Process event attributes.
        
        Args:
            event: Event model
            attributes: Dictionary of attributes
            event_type: Type of event (llm, security, framework, tool, generic)
            related_models: List to append related models to
            db_session: SQLAlchemy session
        """
        # Skip if no attributes
        if not attributes:
            return
        
        # Process session info first to ensure it's available
        self._process_session_info(event, attributes, db_session)
            
        # Process appropriate attributes based on event type    
        if event_type == "llm":
            # Store attributes directly in LLM interaction
            if hasattr(event, 'llm_interaction') and event.llm_interaction:
                # Ensure the interaction has been flushed to get an ID
                db_session.flush()
                
                # Store raw attributes
                event.llm_interaction.raw_attributes = attributes
                
                # Extract known attributes to dedicated columns
                event.llm_interaction.temperature = attributes.get('temperature') or attributes.get('llm.temperature')
                event.llm_interaction.top_p = attributes.get('top_p') or attributes.get('llm.top_p')
                event.llm_interaction.max_tokens = attributes.get('max_tokens') or attributes.get('llm.max_tokens')
                event.llm_interaction.frequency_penalty = attributes.get('frequency_penalty') or attributes.get('llm.frequency_penalty')
                event.llm_interaction.presence_penalty = attributes.get('presence_penalty') or attributes.get('llm.presence_penalty')
                event.llm_interaction.session_id = attributes.get('session.id')
                event.llm_interaction.user_id = attributes.get('user.id')
                event.llm_interaction.prompt_template_id = attributes.get('prompt.template_id')
                event.llm_interaction.stream = attributes.get('stream') or attributes.get('llm.stream')
                event.llm_interaction.cached_response = attributes.get('cached_response') or attributes.get('llm.cached_response')
                event.llm_interaction.model_version = attributes.get('model_version') or attributes.get('llm.model_version')
                
                db_session.add(event.llm_interaction)
                
                # Fix timestamp fields if needed
                self._fix_timestamps(event, event.llm_interaction, db_session)
        
        # Security attributes
        elif event_type == "security" and hasattr(event, 'security_alert') and event.security_alert:
            # Ensure the security alert has been flushed
            db_session.flush()
            
            # Store raw attributes
            event.security_alert.raw_attributes = attributes
            
            # Extract known attributes to dedicated columns if they were added
            if hasattr(event.security_alert, 'detection_source'):
                event.security_alert.detection_source = attributes.get('detection_source') or attributes.get('security.detection_source')
            if hasattr(event.security_alert, 'confidence_score'):
                event.security_alert.confidence_score = attributes.get('confidence_score') or attributes.get('security.confidence_score')
            if hasattr(event.security_alert, 'risk_level'):
                event.security_alert.risk_level = attributes.get('risk_level') or attributes.get('security.risk_level')
            if hasattr(event.security_alert, 'affected_component'):
                event.security_alert.affected_component = attributes.get('affected_component') or attributes.get('security.affected_component')
            if hasattr(event.security_alert, 'detection_rule_id'):
                event.security_alert.detection_rule_id = attributes.get('detection_rule_id') or attributes.get('security.detection_rule_id')
            
            db_session.add(event.security_alert)
            
            # Create security alert triggers if possible
            self._try_create_security_trigger(event.security_alert, db_session)
        
        # Framework attributes
        elif event_type == "framework" and hasattr(event, 'framework_event') and event.framework_event:
            # Ensure the framework event has been flushed
            db_session.flush()
            
            # Store raw attributes
            event.framework_event.raw_attributes = attributes
            
            # Extract known attributes to dedicated columns if they were added
            if hasattr(event.framework_event, 'app_version'):
                event.framework_event.app_version = attributes.get('app_version') or attributes.get('framework.app_version')
            if hasattr(event.framework_event, 'os_type'):
                event.framework_event.os_type = attributes.get('os_type') or attributes.get('framework.os_type')
            if hasattr(event.framework_event, 'memory_usage_mb'):
                event.framework_event.memory_usage_mb = attributes.get('memory_usage_mb') or attributes.get('framework.memory_usage_mb')
            if hasattr(event.framework_event, 'cpu_usage_percent'):
                event.framework_event.cpu_usage_percent = attributes.get('cpu_usage_percent') or attributes.get('framework.cpu_usage_percent')
            if hasattr(event.framework_event, 'environment'):
                event.framework_event.environment = attributes.get('environment') or attributes.get('framework.environment')
            
            db_session.add(event.framework_event)
            
        # Tool attributes
        elif event_type == "tool" and hasattr(event, 'tool_interaction') and event.tool_interaction:
            # Ensure the tool interaction has been flushed
            db_session.flush()
            
            # Store raw attributes
            event.tool_interaction.raw_attributes = attributes
            
            # Extract known attributes to dedicated columns if they were added
            if hasattr(event.tool_interaction, 'tool_version'):
                event.tool_interaction.tool_version = attributes.get('tool_version') or attributes.get('tool.version')
            if hasattr(event.tool_interaction, 'authorization_level'):
                event.tool_interaction.authorization_level = attributes.get('authorization_level') or attributes.get('tool.authorization_level')
            if hasattr(event.tool_interaction, 'execution_time_ms'):
                event.tool_interaction.execution_time_ms = attributes.get('execution_time_ms') or attributes.get('tool.execution_time_ms')
            if hasattr(event.tool_interaction, 'cache_hit'):
                event.tool_interaction.cache_hit = attributes.get('cache_hit') or attributes.get('tool.cache_hit')
            if hasattr(event.tool_interaction, 'api_version'):
                event.tool_interaction.api_version = attributes.get('api_version') or attributes.get('tool.api_version')
            
            db_session.add(event.tool_interaction)
    
    def _process_session_info(self, event: Event, attributes: Dict[str, Any], db_session: Session) -> None:
        """
        Process session information from attributes.
        
        Args:
            event: Event model
            attributes: Dictionary of attributes
            db_session: SQLAlchemy session
        """
        from src.models.session import Session
        from src.models.agent import Agent
        
        # Check if session ID is available in attributes
        session_id = attributes.get('session.id')
        if not session_id:
            return
        
        # Determine the correct agent_id for this session
        # IMPORTANT: Don't blindly use event.agent_id as it might be "unknown-agent"
        # Instead, try to determine the real agent this session belongs to
        
        agent_id = event.agent_id  # Default, but we'll try to find a better one
        
        # Look for better agent identifiers in the attributes
        if 'agent.id' in attributes:
            agent_id = attributes['agent.id']
        elif 'agent.name' in attributes:
            agent_id = attributes['agent.name']
        elif 'application.name' in attributes and attributes['application.name']:
            agent_id = attributes['application.name']
        
        # If event.name contains a known agent pattern, use that
        event_name = event.name or ""
        known_agents = ['weather-agent', 'chatbot-agent', 'rag-agent']
        for known_agent in known_agents:
            if known_agent in event_name:
                agent_id = known_agent
                break
            
        # If we're still using unknown-agent, try one last method with raw_data if available
        if agent_id == "unknown-agent" and event.raw_data:
            raw_data = event.raw_data
            if isinstance(raw_data, dict):
                # Check for signals in raw_data
                raw_name = raw_data.get('name', '')
                for known_agent in known_agents:
                    if known_agent in raw_name:
                        agent_id = known_agent
                        break
        
        # Ensure this agent exists in the DB
        agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            # Create the agent if it doesn't exist
            current_time = datetime.utcnow()
            agent = Agent(
                agent_id=agent_id,
                name=agent_id,
                first_seen=current_time,
                last_seen=current_time,
                is_active=True
            )
            db_session.add(agent)
            db_session.flush()
            logger.debug(f"Created new agent: {agent_id}")
        
        # Debug log to help diagnose issues
        logger.debug(f"Creating/updating session {session_id} for agent {agent_id}")
        
        # Try to get or create the session
        try:
            # First check if it exists
            session = db_session.query(Session).filter(Session.session_id == session_id).first()
            
            if not session:
                # Create it with the agent_id we determined
                current_time = datetime.utcnow()
                session = Session(
                    session_id=session_id,
                    agent_id=agent_id,
                    start_timestamp=current_time,
                    end_timestamp=current_time  # Initialize with same time
                )
                db_session.add(session)
                db_session.flush()
                logger.debug(f"Created new session {session_id} for agent {agent_id}")
            
            # Update event's session ID
            event.session_id = session_id
            db_session.add(event)
            
            # Ensure timestamps are comparable (both naive or both aware)
            event_timestamp = event.timestamp
            session_start = session.start_timestamp
            
            # Make timestamps timezone-naive for comparison if needed
            if hasattr(event_timestamp, 'tzinfo') and event_timestamp.tzinfo is not None:
                # Event timestamp is timezone-aware, make it naive
                event_timestamp = event_timestamp.replace(tzinfo=None)
            
            # Update start_timestamp if this event is earlier
            if session_start is None or event_timestamp < session_start:
                session.start_timestamp = event_timestamp
                db_session.add(session)
                
            # Always update end_timestamp if this event is later than the current end_timestamp
            # or if end_timestamp is not set
            if session.end_timestamp is None or event_timestamp > session.end_timestamp:
                session.end_timestamp = event_timestamp
                db_session.add(session)
            
        except Exception as e:
            logger.error(f"Error processing session information: {str(e)}", exc_info=True)
    
    def _fix_timestamps(self, event: Event, llm_interaction: LLMInteraction, db_session: Session) -> None:
        """
        Fix missing timestamps in LLM interactions by using event timestamps.
        
        Args:
            event: Event model
            llm_interaction: LLM interaction model
            db_session: SQLAlchemy session
        """
        interaction_type = llm_interaction.interaction_type
        
        # Fix missing request timestamp for start interactions
        if interaction_type == 'start' and not llm_interaction.request_timestamp:
            # Use event timestamp or extract from attributes
            if llm_interaction.raw_attributes and 'llm.request.timestamp' in llm_interaction.raw_attributes:
                try:
                    ts_str = llm_interaction.raw_attributes['llm.request.timestamp']
                    # Handle ISO format timestamps
                    ts_str = ts_str.replace('Z', '+00:00')
                    llm_interaction.request_timestamp = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    # Fall back to event timestamp
                    llm_interaction.request_timestamp = event.timestamp
            else:
                llm_interaction.request_timestamp = event.timestamp
                
            db_session.add(llm_interaction)
        
        # Fix missing response timestamp for finish interactions
        if interaction_type == 'finish' and not llm_interaction.response_timestamp:
            # Use event timestamp or extract from attributes
            if llm_interaction.raw_attributes and 'llm.response.timestamp' in llm_interaction.raw_attributes:
                try:
                    ts_str = llm_interaction.raw_attributes['llm.response.timestamp']
                    # Handle ISO format timestamps
                    ts_str = ts_str.replace('Z', '+00:00')
                    llm_interaction.response_timestamp = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    # Fall back to event timestamp
                    llm_interaction.response_timestamp = event.timestamp
            else:
                llm_interaction.response_timestamp = event.timestamp
                
            db_session.add(llm_interaction)
    
    def _try_create_security_trigger(self, security_alert, db_session: Session) -> None:
        """
        Try to create a security alert trigger for the specified alert.
        
        Args:
            security_alert: Security alert model
            db_session: SQLAlchemy session
        """
        from src.models.security_alert import SecurityAlertTrigger
        
        # Get the alert's event
        event = security_alert.event
        if not event:
            return
            
        # First try to find events with matching span_id
        if event.span_id:
            matching_events = db_session.query(Event).filter(
                Event.span_id == event.span_id,
                Event.id != event.id
            ).order_by(Event.timestamp.asc()).all()
            
            if matching_events:
                # Associate with the first event in the span
                trigger_event = matching_events[0]
                logger.info(f"Found matching event {trigger_event.id} with span_id {event.span_id}")
                
                # Create the security alert trigger
                trigger = SecurityAlertTrigger(
                    alert_id=security_alert.id,
                    triggering_event_id=trigger_event.id
                )
                db_session.add(trigger)
                return
                
        # If no matching span_id, try content comparison
        # Look for LLM interactions that might have triggered this alert
        if "suspicious content" in str(security_alert.raw_attributes).lower() or "harmful content" in str(security_alert.raw_attributes).lower():
            # Find recent LLM interactions from the same agent
            potential_triggers = db_session.query(Event).filter(
                Event.agent_id == event.agent_id,
                Event.event_type == "llm",
                Event.timestamp < event.timestamp,
                Event.timestamp > (event.timestamp - timedelta(minutes=5))
            ).order_by(Event.timestamp.desc()).all()
            
            for trigger_event in potential_triggers:
                # Compare content to find the most likely trigger
                if self._compare_security_content(security_alert, trigger_event):
                    logger.info(f"Found matching event {trigger_event.id} through content comparison")
                    
                    # Create the security alert trigger
                    trigger = SecurityAlertTrigger(
                        alert_id=security_alert.id,
                        triggering_event_id=trigger_event.id
                    )
                    db_session.add(trigger)
                    return
                    
        # If no match found, log it for later processing
        logger.warning(f"Could not find matching event for security alert {security_alert.id}")
        
    def _compare_security_content(self, security_alert, event) -> bool:
        """
        Compare security alert content with event content to find matches.
        
        Args:
            security_alert: Security alert model
            event: Event model
            
        Returns:
            bool: True if content matches, False otherwise
        """
        if not security_alert.raw_attributes:
            return False
            
        # Extract relevant content for comparison
        alert_content = str(security_alert.raw_attributes)
        
        # For LLM events, check the LLM interaction raw attributes
        if event.event_type == 'llm' and hasattr(event, 'llm_interaction') and event.llm_interaction:
            if not event.llm_interaction.raw_attributes:
                return False
            event_content = str(event.llm_interaction.raw_attributes)
        else:
            # Fall back to event raw_attributes if available
            if not hasattr(event, 'raw_attributes') or not event.raw_attributes:
                return False
            event_content = str(event.raw_attributes)
        
        # Look for suspicious content patterns
        if "suspicious content in prompt" in alert_content.lower() or "harmful content" in alert_content.lower():
            if "prompt" in event_content.lower() and any(word in event_content.lower() for word in ["harmful", "malicious", "dangerous"]):
                return True
        
        # Look for common identifiers like vendor names
        if "vendor" in alert_content.lower():
            vendor_match = None
            for part in alert_content.lower().split("vendor"):
                if part.strip() and len(part.strip()) > 0:
                    vendor_name = part.split()[0].strip().strip('":,}').lower()
                    if vendor_name and vendor_name in event_content.lower():
                        return True
                
        # Look for common patterns in suspicious content
        suspicious_patterns = [
            "harmful", "malicious", "dangerous", "exploit",
            "injection", "attack", "hack", "breach"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in alert_content.lower() and pattern in event_content.lower():
                return True
                
        return False
    
    def _check_event_as_security_trigger(self, event: Event, db_session: Session) -> None:
        """
        Check if this event could be a trigger for any existing security alerts.
        
        This handles the case where security alerts arrive before their triggering events.
        
        Args:
            event: Event model that might be a trigger
            db_session: SQLAlchemy session
        """
        from src.models.security_alert import SecurityAlert, SecurityAlertTrigger
        
        # Skip if no span_id
        if not event.span_id:
            return
            
        logger.debug(f"Checking if event {event.id} with span_id {event.span_id} could be a security alert trigger")
        
        # Find security alerts with the same span_id that don't have trigger associations
        unassociated_alerts = db_session.query(SecurityAlert).join(
            Event, SecurityAlert.event_id == Event.id
        ).outerjoin(
            SecurityAlertTrigger, SecurityAlertTrigger.alert_id == SecurityAlert.id
        ).filter(
            Event.span_id == event.span_id,
            Event.id != event.id,
            SecurityAlertTrigger.id == None
        ).all()
        
        if unassociated_alerts:
            logger.info(f"Found {len(unassociated_alerts)} unassociated security alerts with matching span_id {event.span_id}")
            
            for alert in unassociated_alerts:
                # Create the security alert trigger
                trigger = SecurityAlertTrigger(
                    alert_id=alert.id,
                    triggering_event_id=event.id
                )
                db_session.add(trigger)
                logger.info(f"Retrospectively associated security alert {alert.id} with event {event.id}")
                
        # If no span matches, try content comparison for LLM interactions
        elif event.event_type == "llm":
            # Find recent unassociated security alerts
            recent_unassociated_alerts = db_session.query(SecurityAlert).join(
                Event, SecurityAlert.event_id == Event.id
            ).outerjoin(
                SecurityAlertTrigger, SecurityAlertTrigger.alert_id == SecurityAlert.id
            ).filter(
                Event.agent_id == event.agent_id,
                Event.timestamp > (event.timestamp - timedelta(minutes=5)),
                Event.timestamp < (event.timestamp + timedelta(minutes=5)),
                SecurityAlertTrigger.id == None
            ).all()
            
            for alert in recent_unassociated_alerts:
                # Compare content
                if self._compare_security_content(alert, event):
                    logger.info(f"Found matching security alert {alert.id} through content comparison")
                    
                    # Create the security alert trigger
                    trigger = SecurityAlertTrigger(
                        alert_id=alert.id,
                        triggering_event_id=event.id
                    )
                    db_session.add(trigger)
                    break  # Only associate with one alert 
    
    def _check_tables_exist(self, db_session) -> bool:
        """
        Check if all required tables exist in the database.
        
        Args:
            db_session: SQLAlchemy session
            
        Returns:
            bool: True if all tables exist, False otherwise
        """
        try:
            # Try a simple query on the agents table as a sanity check
            db_session.query(Agent).first()
            return True
        except Exception as e:
            logger.error(f"Table check failed: {str(e)}")
            return False
            
    def _ensure_agent_exists(self, db_session, agent_id: str) -> None:
        """
        Ensure an agent with the given ID exists, creating it if necessary.
        
        Args:
            db_session: SQLAlchemy session
            agent_id: Agent ID to check/create
        """
        if not agent_id:
            logger.warning("Cannot create agent with empty agent_id")
            return
            
        try:
            # Check if agent exists - IMPORTANT: use agent_id, not id
            agent = db_session.query(Agent).filter(Agent.agent_id == agent_id).first()
            
            # Create agent if it doesn't exist
            if not agent:
                logger.info(f"Creating new agent with ID: {agent_id}")
                current_time = datetime.utcnow()
                agent = Agent(
                    agent_id=agent_id,  # This is the string identifier that will be referenced
                    name=agent_id,  # Use agent_id as the name for consistency
                    first_seen=current_time,
                    last_seen=current_time,
                    is_active=True
                )
                db_session.add(agent)
                db_session.flush()  # Flush to generate ID but don't commit yet
                logger.debug(f"Successfully created agent with agent_id={agent_id}, db id={agent.id}")
            else:
                # Update last_seen time
                agent.last_seen = datetime.utcnow()
                # Ensure name matches agent_id for consistency
                if agent.name != agent_id:
                    agent.name = agent_id
                db_session.add(agent)
                logger.debug(f"Using existing agent with agent_id={agent_id}, db id={agent.id}")
        except Exception as e:
            logger.error(f"Error ensuring agent exists: {str(e)}")
            logger.debug(f"Agent ID: {agent_id}")
            logger.exception(e)
            # Re-raise the exception to be handled by the caller
            raise

# Standalone function for testing and API layer
def process_event(event_data: Dict[str, Any], db_session: Session) -> Event:
    """
    Process a single telemetry event and store it in the database.
    This is a wrapper around SimpleProcessor for the API layer.
    
    Args:
        event_data: Dictionary containing the event data
        db_session: Database session
        
    Returns:
        The created Event object
        
    Raises:
        Exception: If event processing fails
    """
    # Manual validation for required fields
    required_fields = ["timestamp", "name", "level", "agent_id", "trace_id"]
    for field in required_fields:
        if field not in event_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Create event
    try:
        # Parse timestamp
        if isinstance(event_data["timestamp"], str):
            timestamp = datetime.fromisoformat(event_data["timestamp"].replace('Z', '+00:00'))
        else:
            timestamp = event_data["timestamp"]
            
        # Create event object
        event = Event(
            schema_version=event_data.get("schema_version", "1.0"),
            timestamp=timestamp,
            trace_id=event_data["trace_id"],
            span_id=event_data.get("span_id"),
            parent_span_id=event_data.get("parent_span_id"),
            name=event_data["name"],
            level=event_data["level"],
            agent_id=event_data["agent_id"],
            attributes=event_data.get("attributes", {}),
            raw_data=event_data  # Store the entire event data in raw_data
        )
        
        # Add to session
        db_session.add(event)
        db_session.commit()
        
        return event
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        raise 