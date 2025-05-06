"""
LLM interaction model and related functionality.

This module defines the LLMInteraction model for storing LLM interactions
from telemetry events.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base


class LLMInteraction(Base):
    """
    LLM Interaction model for LLM API call events.
    
    This model represents LLM API calls, storing details about the request,
    response, token usage, and other metadata.
    """
    __tablename__ = "llm_interactions"
    
    # Adding table_args with extend_existing=True to fix SQLAlchemy error
    __table_args__ = (
        {"extend_existing": True}
    )
    
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
        
        # Extract configuration parameters using vendor-specific methods
        vendor = payload.get('vendor', '')
        config_params = cls._extract_config_parameters(attributes, vendor)
        
        # Create LLM interaction
        llm_interaction = cls(
            event_id=event.id,
            interaction_type=interaction_type,
            vendor=vendor,
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
            
            # Extract config parameters using the extracted values
            temperature=config_params.get('temperature'),
            top_p=config_params.get('top_p'),
            max_tokens=config_params.get('max_tokens'),
            frequency_penalty=config_params.get('frequency_penalty'),
            presence_penalty=config_params.get('presence_penalty'),
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
        
        # Extract vendor for vendor-specific parameter handling
        vendor = attributes.get('llm.vendor', '')
        
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
        
        # Extract request data to look for configuration parameters
        request_data = attributes.get('llm.request.data', {})
        
        # First try standard attribute extraction
        config_params = cls._extract_config_parameters(attributes, vendor)
        
        # If any of the config parameters are still missing, try to extract from request_data
        if not config_params.get('temperature') or not config_params.get('max_tokens'):
            config_params_from_request = cls._extract_config_from_request_data(request_data, vendor)
            # Update missing parameters
            for param, value in config_params_from_request.items():
                if not config_params.get(param):
                    config_params[param] = value
        
        # Parse response content if available
        response_content = None
        if attributes.get('llm.response.content'):
            try:
                if isinstance(attributes.get('llm.response.content'), str):
                    response_content = json.loads(attributes.get('llm.response.content'))
                else:
                    response_content = attributes.get('llm.response.content')
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse response content as JSON: {attributes.get('llm.response.content')}")
                response_content = attributes.get('llm.response.content')
        
        # Extract additional metadata fields
        session_id = attributes.get('session.id')
        user_id = attributes.get('user.id') or attributes.get('llm.user.id')
        prompt_template_id = attributes.get('prompt.template_id') or attributes.get('llm.prompt.template_id')
        
        # Extract stream flag
        stream = attributes.get('stream') or attributes.get('llm.stream')
        if stream is not None:
            stream = bool(stream)
        
        # Extract cached_response flag
        cached_response = attributes.get('cached_response') or attributes.get('llm.cached_response') or attributes.get('llm.response.cached')
        if cached_response is not None:
            cached_response = bool(cached_response)
        
        # Extract model_version
        model_version = attributes.get('model_version') or attributes.get('llm.model_version') or attributes.get('llm.model.version')
        
        # Create LLM interaction
        llm_interaction = cls(
            event_id=event.id,
            interaction_type=interaction_type,
            vendor=vendor,
            model=attributes.get('llm.model', ''),
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            duration_ms=attributes.get('llm.response.duration_ms'),
            input_tokens=attributes.get('llm.usage.input_tokens'),
            output_tokens=attributes.get('llm.usage.output_tokens'),
            total_tokens=attributes.get('llm.usage.total_tokens'),
            request_data=request_data,
            response_content=response_content,
            response_id=attributes.get('llm.response.id'),
            stop_reason=attributes.get('llm.response.stop_reason'),
            raw_attributes=attributes,  # Store raw attributes
            
            # Configuration parameters
            temperature=config_params.get('temperature'),
            top_p=config_params.get('top_p'),
            max_tokens=config_params.get('max_tokens'),
            frequency_penalty=config_params.get('frequency_penalty'),
            presence_penalty=config_params.get('presence_penalty'),
            
            # Additional metadata fields
            session_id=session_id,
            user_id=user_id,
            prompt_template_id=prompt_template_id,
            stream=stream,
            cached_response=cached_response,
            model_version=model_version
        )
        
        db_session.add(llm_interaction)
        
        # Try to link with related interactions
        if interaction_type == 'start':
            cls._try_link_with_finish(db_session, event, llm_interaction)
        else:  # 'finish'
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
    
    @classmethod
    def _extract_config_parameters(cls, attributes: Dict[str, Any], vendor: str) -> Dict[str, Any]:
        """
        Extract configuration parameters from attributes with vendor-specific handling.
        
        Args:
            attributes: Dictionary of attributes
            vendor: LLM vendor name (e.g., 'openai', 'anthropic')
            
        Returns:
            Dict containing extracted parameters
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug parameter extraction
        logger.debug(f"Extracting config parameters for vendor: {vendor}")
        
        # First try standard parameter formats (direct attributes)
        params = {
            'temperature': attributes.get('temperature') or attributes.get('llm.temperature') 
                          or attributes.get('llm.request.temperature'),
            'max_tokens': attributes.get('max_tokens') or attributes.get('llm.max_tokens') 
                         or attributes.get('llm.request.max_tokens'),
            'top_p': attributes.get('top_p') or attributes.get('llm.top_p'),
            'frequency_penalty': attributes.get('frequency_penalty') or attributes.get('llm.frequency_penalty'),
            'presence_penalty': attributes.get('presence_penalty') or attributes.get('llm.presence_penalty')
        }
        
        # Debug extracted parameters
        logger.debug(f"Standard parameter extraction results:")
        logger.debug(f"  temperature: {params['temperature']}")
        logger.debug(f"  max_tokens: {params['max_tokens']}")
        
        # If vendor-specific extraction is needed and standard extraction failed
        if not params['temperature'] or not params['max_tokens']:
            # Convert vendor to lowercase for case-insensitive comparison
            vendor_lower = vendor.lower()
            
            if vendor_lower == 'openai':
                vendor_params = cls._extract_openai_params(attributes)
            elif vendor_lower == 'anthropic':
                vendor_params = cls._extract_anthropic_params(attributes)
            elif vendor_lower == 'cohere':
                vendor_params = cls._extract_cohere_params(attributes)
            else:
                # Generic fallback
                vendor_params = {}
            
            # Update params with vendor-specific values for missing parameters
            for param, value in vendor_params.items():
                if not params.get(param) and value is not None:
                    params[param] = value
                    logger.debug(f"Updated {param} to {value} from vendor-specific extraction")
        
        # One last attempt: check if the parameters are in the request_data
        if (not params['temperature'] or not params['max_tokens']) and 'llm.request.data' in attributes:
            try:
                request_data = attributes['llm.request.data']
                if isinstance(request_data, str):
                    import json
                    request_data = json.loads(request_data)
                
                # Extract parameters directly from request_data
                if not params['temperature'] and 'temperature' in request_data:
                    params['temperature'] = request_data['temperature']
                    logger.debug(f"Extracted temperature {params['temperature']} from request_data")
                
                if not params['max_tokens'] and 'max_tokens' in request_data:
                    params['max_tokens'] = request_data['max_tokens']
                    logger.debug(f"Extracted max_tokens {params['max_tokens']} from request_data")
                
                # Check for vendor-specific parameter names in request_data
                if vendor.lower() == 'anthropic' and not params['max_tokens'] and 'max_tokens_to_sample' in request_data:
                    params['max_tokens'] = request_data['max_tokens_to_sample']
                    logger.debug(f"Extracted max_tokens {params['max_tokens']} from request_data.max_tokens_to_sample")
            except Exception as e:
                logger.error(f"Error extracting parameters from request_data: {str(e)}")
        
        # Debug final extracted values
        logger.debug(f"Final extracted parameters:")
        logger.debug(f"  temperature: {params['temperature']}")
        logger.debug(f"  max_tokens: {params['max_tokens']}")
        
        return params
    
    @classmethod
    def _extract_config_from_request_data(cls, request_data: Dict[str, Any], vendor: str) -> Dict[str, Any]:
        """
        Extract configuration parameters from request_data field.
        
        Args:
            request_data: Dictionary containing request data
            vendor: LLM vendor name
            
        Returns:
            Dict containing extracted parameters
        """
        params = {}
        
        # Common parameters generally available in request_data
        if request_data:
            params['temperature'] = request_data.get('temperature')
            params['max_tokens'] = request_data.get('max_tokens')
            params['top_p'] = request_data.get('top_p')
            params['frequency_penalty'] = request_data.get('frequency_penalty')
            params['presence_penalty'] = request_data.get('presence_penalty')
            
            # Handle vendor-specific formats in request_data
            vendor_lower = vendor.lower()
            
            if vendor_lower == 'anthropic':
                # Anthropic might use max_tokens_to_sample instead of max_tokens
                if not params.get('max_tokens') and request_data.get('max_tokens_to_sample'):
                    params['max_tokens'] = request_data.get('max_tokens_to_sample')
            
            elif vendor_lower == 'cohere':
                # Cohere might use maxTokens instead of max_tokens
                if not params.get('max_tokens') and request_data.get('maxTokens'):
                    params['max_tokens'] = request_data.get('maxTokens')
            
            # Check for camelCase variants that might exist in some vendor formats
            if not params.get('max_tokens') and request_data.get('maxTokens'):
                params['max_tokens'] = request_data.get('maxTokens')
                
            if not params.get('top_p') and request_data.get('topP'):
                params['top_p'] = request_data.get('topP')
                
            if not params.get('frequency_penalty') and request_data.get('frequencyPenalty'):
                params['frequency_penalty'] = request_data.get('frequencyPenalty')
                
            if not params.get('presence_penalty') and request_data.get('presencePenalty'):
                params['presence_penalty'] = request_data.get('presencePenalty')
        
        return params
    
    @classmethod
    def _extract_openai_params(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract OpenAI-specific parameters from attributes.
        
        Args:
            attributes: Dictionary of attributes
            
        Returns:
            Dict containing extracted parameters
        """
        params = {}
        
        # Check for OpenAI format variations
        for prefix in ['', 'openai.', 'llm.openai.', 'openai.request.', 'llm.openai.request.']:
            # Check for temperature
            temp_key = f"{prefix}temperature"
            if temp_key in attributes and attributes[temp_key] is not None:
                params['temperature'] = attributes[temp_key]
                
            # Check for max_tokens
            max_tokens_key = f"{prefix}max_tokens"
            if max_tokens_key in attributes and attributes[max_tokens_key] is not None:
                params['max_tokens'] = attributes[max_tokens_key]
                
            # Check for top_p
            top_p_key = f"{prefix}top_p"
            if top_p_key in attributes and attributes[top_p_key] is not None:
                params['top_p'] = attributes[top_p_key]
                
            # Check for frequency_penalty
            freq_key = f"{prefix}frequency_penalty"
            if freq_key in attributes and attributes[freq_key] is not None:
                params['frequency_penalty'] = attributes[freq_key]
                
            # Check for presence_penalty
            pres_key = f"{prefix}presence_penalty"
            if pres_key in attributes and attributes[pres_key] is not None:
                params['presence_penalty'] = attributes[pres_key]
        
        # Also check for these parameters in the request data if it exists
        if 'llm.request.data' in attributes:
            try:
                request_data = attributes['llm.request.data']
                if isinstance(request_data, str):
                    import json
                    request_data = json.loads(request_data)
                    
                # Now extract parameters
                if 'temperature' in request_data and not params.get('temperature'):
                    params['temperature'] = request_data['temperature']
                    
                if 'max_tokens' in request_data and not params.get('max_tokens'):
                    params['max_tokens'] = request_data['max_tokens']
                    
                if 'top_p' in request_data and not params.get('top_p'):
                    params['top_p'] = request_data['top_p']
                    
                if 'frequency_penalty' in request_data and not params.get('frequency_penalty'):
                    params['frequency_penalty'] = request_data['frequency_penalty']
                    
                if 'presence_penalty' in request_data and not params.get('presence_penalty'):
                    params['presence_penalty'] = request_data['presence_penalty']
            except Exception:
                # If we fail to parse, just continue
                pass
        
        return params
    
    @classmethod
    def _extract_anthropic_params(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract Anthropic-specific parameters from attributes.
        
        Args:
            attributes: Dictionary of attributes
            
        Returns:
            Dict containing extracted parameters
        """
        params = {}
        
        # Check for Anthropic format variations
        for prefix in ['', 'anthropic.', 'llm.anthropic.', 'anthropic.request.', 'llm.anthropic.request.']:
            # Check for temperature
            temp_key = f"{prefix}temperature"
            if temp_key in attributes and attributes[temp_key] is not None:
                params['temperature'] = attributes[temp_key]
                
            # Anthropic uses max_tokens_to_sample instead of max_tokens
            max_tokens_key = f"{prefix}max_tokens_to_sample"
            if max_tokens_key in attributes and attributes[max_tokens_key] is not None:
                params['max_tokens'] = attributes[max_tokens_key]
                
            # Also check the standard format
            std_max_tokens_key = f"{prefix}max_tokens"
            if std_max_tokens_key in attributes and attributes[std_max_tokens_key] is not None:
                params['max_tokens'] = attributes[std_max_tokens_key]
                
            # Check for top_p
            top_p_key = f"{prefix}top_p"
            if top_p_key in attributes and attributes[top_p_key] is not None:
                params['top_p'] = attributes[top_p_key]
        
        # Also check for these parameters in the request data if it exists
        if 'llm.request.data' in attributes:
            try:
                request_data = attributes['llm.request.data']
                if isinstance(request_data, str):
                    import json
                    request_data = json.loads(request_data)
                    
                # Now extract parameters
                if 'temperature' in request_data and not params.get('temperature'):
                    params['temperature'] = request_data['temperature']
                    
                # Anthropic uses max_tokens_to_sample instead of max_tokens in many cases
                if 'max_tokens_to_sample' in request_data and not params.get('max_tokens'):
                    params['max_tokens'] = request_data['max_tokens_to_sample']
                    
                # But also check for standard format
                if 'max_tokens' in request_data and not params.get('max_tokens'):
                    params['max_tokens'] = request_data['max_tokens']
                    
                if 'top_p' in request_data and not params.get('top_p'):
                    params['top_p'] = request_data['top_p']
            except Exception:
                # If we fail to parse, just continue
                pass
        
        return params
    
    @classmethod
    def _extract_cohere_params(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract Cohere-specific parameters from attributes.
        
        Args:
            attributes: Dictionary of attributes
            
        Returns:
            Dict containing extracted parameters
        """
        params = {}
        
        # Check for Cohere format variations
        for prefix in ['', 'cohere.', 'llm.cohere.', 'cohere.request.', 'llm.cohere.request.']:
            # Check for temperature
            temp_key = f"{prefix}temperature"
            if temp_key in attributes and attributes[temp_key] is not None:
                params['temperature'] = attributes[temp_key]
                
            # Check for max_tokens
            max_tokens_key = f"{prefix}max_tokens"
            if max_tokens_key in attributes and attributes[max_tokens_key] is not None:
                params['max_tokens'] = attributes[max_tokens_key]
                
            # Check for top_p
            top_p_key = f"{prefix}top_p"
            if top_p_key in attributes and attributes[top_p_key] is not None:
                params['top_p'] = attributes[top_p_key]
        
        # Also check for these parameters in the request data if it exists
        if 'llm.request.data' in attributes:
            try:
                request_data = attributes['llm.request.data']
                if isinstance(request_data, str):
                    import json
                    request_data = json.loads(request_data)
                    
                # Now extract parameters
                if 'temperature' in request_data and not params.get('temperature'):
                    params['temperature'] = request_data['temperature']
                    
                # Check for standard format
                if 'max_tokens' in request_data and not params.get('max_tokens'):
                    params['max_tokens'] = request_data['max_tokens']
                    
                # Check for camelCase variants (Cohere often uses camelCase)
                if 'maxTokens' in request_data and not params.get('max_tokens'):
                    params['max_tokens'] = request_data['maxTokens']
                    
                if 'top_p' in request_data and not params.get('top_p'):
                    params['top_p'] = request_data['top_p']
                    
                # Check for camelCase variant
                if 'topP' in request_data and not params.get('top_p'):
                    params['top_p'] = request_data['topP']
                    
                # Check for frequency penalty
                if 'frequencyPenalty' in request_data and not params.get('frequency_penalty'):
                    params['frequency_penalty'] = request_data['frequencyPenalty']
                    
                # Check for presence penalty
                if 'presencePenalty' in request_data and not params.get('presence_penalty'):
                    params['presence_penalty'] = request_data['presencePenalty']
            except Exception:
                # If we fail to parse, just continue
                pass
        
        return params 