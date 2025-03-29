"""
LLM Interaction model and related functionality.

This module defines the LLMInteraction model for LLM API call events.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship

from models.base import Base


class LLMInteraction(Base):
    """
    LLM Interaction model for LLM API call events.
    
    This model represents LLM API calls, storing details about the request,
    response, token usage, and other metadata.
    """
    __tablename__ = "llm_interactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    interaction_type = Column(String, nullable=False, index=True)  # 'start' or 'finish'
    vendor = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    request_timestamp = Column(DateTime, index=True)
    response_timestamp = Column(DateTime, index=True)
    duration_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    request_data = Column(JSON)
    response_content = Column(JSON)
    response_id = Column(String)
    stop_reason = Column(String)
    
    # New fields added in Task 04-01
    related_interaction_id = Column(Integer, ForeignKey("llm_interactions.id"), nullable=True)
    
    # Extracted attribute fields for better querying
    temperature = Column(Float)
    top_p = Column(Float)
    max_tokens = Column(Integer)
    frequency_penalty = Column(Float)
    presence_penalty = Column(Float)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True)
    prompt_template_id = Column(String, index=True)
    stream = Column(Boolean)
    cached_response = Column(Boolean)
    model_version = Column(String)
    
    # Raw attributes JSON storage for complete data
    raw_attributes = Column(JSON)
    
    # Relationships
    event = relationship("Event", back_populates="llm_interaction")
    
    # Self-referential relationship for related start/finish interactions
    related_interaction = relationship(
        "LLMInteraction",
        foreign_keys=[related_interaction_id],
        remote_side=[id],
        uselist=False,
        post_update=True
    )
    
    def __repr__(self) -> str:
        return f"<LLMInteraction {self.id} ({self.interaction_type})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data: Dict[str, Any] = None) -> "LLMInteraction":
        """
        Create an LLMInteraction from an event.
        
        Args:
            db_session: Database session
            event: The parent event
            telemetry_data: Optional telemetry data
            
        Returns:
            LLMInteraction: The created LLM interaction
        """
        # Debug logs for troubleshooting
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Creating LLM interaction for event ID: {event.id}, name: {event.name}")
        
        # Log the structure of telemetry_data
        if telemetry_data:
            logger.debug(f"Telemetry data type: {type(telemetry_data)}")
            logger.debug(f"Telemetry data keys: {list(telemetry_data.keys())}")
            
            # Check for attributes key
            if 'attributes' in telemetry_data:
                logger.debug(f"Attributes found in telemetry_data")
                logger.debug(f"Attribute keys: {list(telemetry_data['attributes'].keys())}")
                logger.debug(f"LLM-related keys: {[k for k in telemetry_data['attributes'].keys() if k.startswith('llm.')]}")
                
                # Check for specific important keys
                for key in ['llm.vendor', 'llm.model', 'llm.request.timestamp']:
                    logger.debug(f"{key} present: {key in telemetry_data['attributes']}")
                    if key in telemetry_data['attributes']:
                        logger.debug(f"{key} value: {telemetry_data['attributes'][key]}")
        else:
            logger.debug("No telemetry_data provided")
            logger.debug(f"Event data attribute: {hasattr(event, 'data')}")
            if hasattr(event, 'data'):
                logger.debug(f"Event data value: {event.data}")
            
        # If telemetry_data is provided, use the method with telemetry support
        if telemetry_data:
            try:
                return cls.from_event_with_telemetry(db_session, event, telemetry_data)
            except Exception as e:
                logger.error(f"Error creating LLM interaction with telemetry: {str(e)}")
                logger.exception(e)
                return None
        
        # Original implementation for backward compatibility
        if not hasattr(event, 'data') or not event.data:
            logger.error("Event data is required to create an LLM interaction but it's missing")
            raise ValueError("Event data is required to create an LLM interaction")
            
        try:
            logger.debug(f"Attempting to parse event.data: {event.data}")
            event_data = json.loads(event.data)
            logger.debug(f"Parsed event_data keys: {list(event_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event.data as JSON: {str(e)}")
            raise ValueError("Event data must be valid JSON")
            
        payload = event_data.get("payload", {})
        logger.debug(f"Payload keys: {list(payload.keys())}")
        
        # Determine interaction type from event name
        interaction_type = 'start' if event.name == 'llm.call.start' else 'finish'
        
        # Extract attributes from payload
        attributes = payload.get('attributes', {})
        
        # Create LLM interaction
        llm_interaction = cls(
            event_id=event.id,
            interaction_type=interaction_type,
            vendor=payload.get('vendor', ''),
            model=payload.get('model', ''),
            request_timestamp=event.timestamp if interaction_type == 'start' else None,
            response_timestamp=event.timestamp if interaction_type == 'finish' else None,
            duration_ms=payload.get('duration_ms'),
            input_tokens=payload.get('input_tokens'),
            output_tokens=payload.get('output_tokens'),
            total_tokens=payload.get('total_tokens'),
            request_data=payload.get('request_data'),
            response_content=payload.get('response_content'),
            response_id=payload.get('response_id'),
            stop_reason=payload.get('stop_reason'),
            raw_attributes=attributes,  # Store raw attributes
            
            # Extract known attributes to dedicated columns
            temperature=attributes.get('temperature'),
            top_p=attributes.get('top_p'),
            max_tokens=attributes.get('max_tokens'),
            frequency_penalty=attributes.get('frequency_penalty'),
            presence_penalty=attributes.get('presence_penalty'),
            session_id=attributes.get('session.id'),
            user_id=attributes.get('user.id'),
            prompt_template_id=attributes.get('prompt.template_id'),
            stream=attributes.get('stream'),
            cached_response=attributes.get('cached_response'),
            model_version=attributes.get('model_version')
        )
        
        db_session.add(llm_interaction)
        logger.debug(f"Created LLM interaction in db_session, type: {interaction_type}")
        
        # Look for related interaction to link
        if interaction_type == 'start':
            cls._try_link_with_finish(db_session, event, llm_interaction)
        else: # 'finish'
            cls._try_link_with_start(db_session, event, llm_interaction)
        
        return llm_interaction
    
    @classmethod
    def from_event_with_telemetry(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "LLMInteraction":
        """
        Create an LLMInteraction from an event and telemetry data.
        
        Args:
            db_session: Database session
            event: The parent event
            telemetry_data: Telemetry data as a dictionary
            
        Returns:
            LLMInteraction: The created LLM interaction
        """
        import logging
        logger = logging.getLogger(__name__)
        
        attributes = telemetry_data.get('attributes', {})
        
        # Determine interaction type from event name
        interaction_type = 'start' if event.name == 'llm.call.start' else 'finish'
        
        # Get request timestamp
        request_timestamp = None
        if attributes.get('llm.request.timestamp'):
            try:
                request_timestamp = datetime.fromisoformat(
                    attributes.get('llm.request.timestamp').replace('Z', '+00:00')
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid request timestamp: {attributes.get('llm.request.timestamp')}, error: {str(e)}")
        
        # Get response timestamp
        response_timestamp = None
        if attributes.get('llm.response.timestamp'):
            try:
                response_timestamp = datetime.fromisoformat(
                    attributes.get('llm.response.timestamp').replace('Z', '+00:00')
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid response timestamp: {attributes.get('llm.response.timestamp')}, error: {str(e)}")
        
        # Create LLM interaction
        llm_interaction = cls(
            event_id=event.id,
            interaction_type=interaction_type,
            vendor=attributes.get('llm.vendor', ''),
            model=attributes.get('llm.model', ''),
            request_timestamp=request_timestamp if interaction_type == 'start' else None,
            response_timestamp=response_timestamp if interaction_type == 'finish' else None,
            duration_ms=attributes.get('llm.response.duration_ms'),
            input_tokens=attributes.get('llm.usage.input_tokens'),
            output_tokens=attributes.get('llm.usage.output_tokens'),
            total_tokens=attributes.get('llm.usage.total_tokens'),
            request_data=attributes.get('llm.request.data'),
            response_content=attributes.get('llm.response.content'),
            response_id=attributes.get('llm.response.id'),
            stop_reason=attributes.get('llm.response.stop_reason'),
            raw_attributes=attributes,  # Store raw attributes
            
            # Extract known attributes to dedicated columns
            temperature=attributes.get('llm.temperature'),
            top_p=attributes.get('llm.top_p'),
            max_tokens=attributes.get('llm.max_tokens'),
            frequency_penalty=attributes.get('llm.frequency_penalty'),
            presence_penalty=attributes.get('llm.presence_penalty'),
            session_id=attributes.get('session.id'),
            user_id=attributes.get('user.id'),
            prompt_template_id=attributes.get('prompt.template_id'),
            stream=attributes.get('llm.stream'),
            cached_response=attributes.get('llm.cached_response'),
            model_version=attributes.get('llm.model_version')
        )
        
        db_session.add(llm_interaction)
        
        # Look for related interaction to link
        if interaction_type == 'start':
            cls._try_link_with_finish(db_session, event, llm_interaction)
        else: # 'finish'
            cls._try_link_with_start(db_session, event, llm_interaction)
            
        return llm_interaction
    
    @classmethod
    def _try_link_with_finish(cls, db_session, event, start_interaction):
        """Try to find and link with a corresponding finish interaction."""
        import logging
        logger = logging.getLogger(__name__)
        
        if not event.trace_id or not event.span_id:
            return
            
        # Look for a finish interaction with the same trace_id and span_id
        from sqlalchemy.orm import aliased
        FinishEvent = aliased(type(event))
        
        finish_interaction = db_session.query(cls).join(
            FinishEvent, cls.event_id == FinishEvent.id
        ).filter(
            FinishEvent.trace_id == event.trace_id,
            FinishEvent.span_id == event.span_id,
            cls.interaction_type == 'finish',
            FinishEvent.id != event.id
        ).first()
        
        if finish_interaction:
            logger.debug(f"Linking start interaction {start_interaction.id} with finish interaction {finish_interaction.id}")
            start_interaction.related_interaction_id = finish_interaction.id
            finish_interaction.related_interaction_id = start_interaction.id
            db_session.add(finish_interaction)
    
    @classmethod
    def _try_link_with_start(cls, db_session, event, finish_interaction):
        """Try to find and link with a corresponding start interaction."""
        import logging
        logger = logging.getLogger(__name__)
        
        if not event.trace_id or not event.span_id:
            return
            
        # Look for a start interaction with the same trace_id and span_id
        from sqlalchemy.orm import aliased
        StartEvent = aliased(type(event))
        
        start_interaction = db_session.query(cls).join(
            StartEvent, cls.event_id == StartEvent.id
        ).filter(
            StartEvent.trace_id == event.trace_id,
            StartEvent.span_id == event.span_id,
            cls.interaction_type == 'start',
            StartEvent.id != event.id
        ).first()
        
        if start_interaction:
            logger.debug(f"Linking finish interaction {finish_interaction.id} with start interaction {start_interaction.id}")
            finish_interaction.related_interaction_id = start_interaction.id
            start_interaction.related_interaction_id = finish_interaction.id
            db_session.add(start_interaction)
    
    def get_cost_estimate(self, input_price_per_1k: float = 0.0, output_price_per_1k: float = 0.0) -> float:
        """
        Calculate an estimated cost for this interaction based on token usage.
        
        Args:
            input_price_per_1k: Price per 1,000 input tokens
            output_price_per_1k: Price per 1,000 output tokens
            
        Returns:
            float: Estimated cost in dollars
        """
        if self.input_tokens is None or self.output_tokens is None:
            return 0.0
            
        input_cost = (self.input_tokens / 1000) * input_price_per_1k
        output_cost = (self.output_tokens / 1000) * output_price_per_1k
        
        return input_cost + output_cost
    
    def get_attribute(self, key: str, default=None) -> Any:
        """
        Get an attribute value by key.
        
        Args:
            key: Attribute key
            default: Default value if attribute doesn't exist
            
        Returns:
            The attribute value, or default if not found
        """
        if self.raw_attributes is None:
            return default
            
        return self.raw_attributes.get(key, default)
    
    def set_attribute(self, db_session, key: str, value: Any) -> None:
        """
        Set an attribute value.
        
        Args:
            db_session: Database session
            key: Attribute key
            value: Attribute value
        """
        if self.raw_attributes is None:
            self.raw_attributes = {}
            
        self.raw_attributes[key] = value
        db_session.add(self)
    
    def get_attributes(self) -> Dict[str, Any]:
        """
        Get all attributes as a dictionary.
        
        Returns:
            Dict: All attributes
        """
        return self.raw_attributes or {}
    
    def get_request_content(self) -> List[str]:
        """
        Extract the request content as a list of strings.
        
        Returns:
            List[str]: Request content
        """
        if not self.request_data:
            return []
            
        messages = self.request_data.get("messages", [])
        content = []
        
        for message in messages:
            if isinstance(message, dict) and "content" in message:
                message_content = message["content"]
                if isinstance(message_content, str):
                    content.append(message_content)
                elif isinstance(message_content, list):
                    for item in message_content:
                        if isinstance(item, dict) and "text" in item:
                            content.append(item["text"])
        
        return content
    
    def get_response_content(self) -> List[str]:
        """
        Extract the response content as a list of strings.
        
        Returns:
            List[str]: Response content
        """
        if not self.response_content:
            return []
            
        if isinstance(self.response_content, list):
            content = []
            for item in self.response_content:
                if isinstance(item, dict) and "text" in item:
                    content.append(item["text"])
            return content
        
        return [str(self.response_content)] 