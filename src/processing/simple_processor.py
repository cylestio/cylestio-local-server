"""
Simple processor for telemetry events.

This module provides a simple processor for validating and storing telemetry
events in the database.
"""
import json
import logging
from typing import Dict, Any, List, Union, Optional, Tuple
from datetime import datetime, UTC, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.event import Event
from models.agent import Agent
from models.trace import Trace
from models.span import Span
from models.llm_interaction import LLMInteraction
from models.security_alert import SecurityAlert
from models.framework_event import FrameworkEvent

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
        Process a single telemetry event.
        
        Args:
            event_data: Dictionary containing the event data
            
        Returns:
            Dict with processing results
        """
        # Validate the event data
        validation_result = self._validate_event(event_data)
        if not validation_result["valid"]:
            return {
                "success": False, 
                "error": validation_result["error"],
                "details": validation_result.get("details", {})
            }
        
        # Create database session - get the actual session from the generator
        db_session = next(self.db_session_factory())
        
        try:
            # Process the event
            event, related_models = self._transform_event(event_data, db_session)
            
            # Add to session
            db_session.add(event)
            for model in related_models:
                db_session.add(model)
                
            # Commit
            db_session.commit()
            
            return {
                "success": True,
                "event_id": event.id,
                "event_name": event.name
            }
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error processing event: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": e.__class__.__name__}
            }
            
        finally:
            db_session.close()
    
    def process_json_event(self, json_data: str) -> Dict[str, Any]:
        """
        Process a single event from JSON string.
        
        Args:
            json_data: JSON string containing event data
            
        Returns:
            Dict with processing results
        """
        try:
            event_data = json.loads(json_data)
            return self.process_event(event_data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}",
                "details": {"json_sample": json_data[:100] + "..." if len(json_data) > 100 else json_data}
            }
    
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
        Process a batch of events from JSON string.
        
        The JSON should be an array of event objects.
        
        Args:
            json_data: JSON string containing an array of events
            
        Returns:
            Dict with batch processing results
        """
        try:
            events_data = json.loads(json_data)
            if not isinstance(events_data, list):
                return {
                    "success": False,
                    "error": "JSON must contain an array of events",
                    "details": {"type": type(events_data).__name__}
                }
            
            return self.process_batch(events_data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}",
                "details": {"json_sample": json_data[:100] + "..." if len(json_data) > 100 else json_data}
            }
    
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
            current_time = datetime.now(UTC)
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
        
        # Handle span if present
        span = None
        if "span_id" in event_data and event_data["span_id"]:
            span = db_session.query(Span).filter_by(span_id=event_data["span_id"]).first()
            if not span:
                span = Span(
                    span_id=event_data["span_id"],
                    trace_id=event_data.get("trace_id"),
                    parent_span_id=event_data.get("parent_span_id")
                )
                if trace:
                    span.trace = trace
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
        timestamp_dt = datetime.fromisoformat(event_data["timestamp"].replace('Z', '+00:00'))
        event = Event(
            name=event_data["name"],
            timestamp=timestamp_dt,
            level=event_data["level"],
            agent_id=event_data["agent_id"],
            trace_id=event_data.get("trace_id"),
            span_id=event_data.get("span_id"),
            parent_span_id=event_data.get("parent_span_id"),
            schema_version=event_data.get("schema_version", "1.0"),
            event_type=event_type
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
            specialized_event = SecurityAlert.from_event(db_session, event, event_data)
        elif event_type == "framework":
            specialized_event = FrameworkEvent.from_event(db_session, event, event_data)
        elif event_type == "tool":
            try:
                # Import here to avoid circular imports
                from models.tool_interaction import ToolInteraction
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
        from models.session import Session
        
        # Check if session ID is available in attributes
        session_id = attributes.get('session.id')
        if not session_id:
            return
        
        # Try to get or create the session
        session = Session.get_or_create(db_session, session_id, event.agent_id)
        
        # Update event's session ID
        event.session_id = session_id
        db_session.add(event)
        
        # Update session end timestamp if needed
        if session.end_timestamp is None or event.timestamp > session.end_timestamp:
            session.update_end_timestamp(db_session, event.timestamp)
    
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
        from models.security_alert import SecurityAlertTrigger
        
        # Get the alert's event
        event = security_alert.event
        if not event:
            return
            
        # Find potential triggering events
        # (events from the same agent that occurred shortly before the alert)
        potential_triggers = db_session.query(Event).filter(
            Event.agent_id == event.agent_id,
            Event.timestamp < event.timestamp,
            Event.timestamp > (event.timestamp - timedelta(minutes=1)),
            Event.id != event.id
        ).order_by(Event.timestamp.desc()).limit(1).all()
        
        if potential_triggers:
            trigger_event = potential_triggers[0]
            
            # Create the security alert trigger
            trigger = SecurityAlertTrigger(
                alert_id=security_alert.id,
                triggering_event_id=trigger_event.id
            )
            
            db_session.add(trigger) 