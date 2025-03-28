"""
LLM Interaction model and related functionality.

This module defines the LLMInteraction model for LLM API call events.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base


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
    
    # Relationships
    event = relationship("Event", back_populates="llm_interaction")
    attributes = relationship(
        "LLMAttribute", 
        back_populates="llm_interaction",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<LLMInteraction {self.id} ({self.interaction_type})>"
    
    @classmethod
    def from_event(cls, db_session, event, telemetry_data: Dict[str, Any]) -> "LLMInteraction":
        """
        Create an LLMInteraction from an event and telemetry data.
        
        Args:
            db_session: Database session
            event: The parent event
            telemetry_data: Telemetry data as a dictionary
            
        Returns:
            LLMInteraction: The created LLM interaction
        """
        attributes = telemetry_data.get('attributes', {})
        
        # Determine interaction type from event name
        interaction_type = 'start' if event.name == 'llm.call.start' else 'finish'
        
        # Get request timestamp
        request_timestamp = None
        if attributes.get('llm.request.timestamp'):
            request_timestamp = datetime.fromisoformat(
                attributes.get('llm.request.timestamp').replace('Z', '+00:00')
            )
        
        # Get response timestamp
        response_timestamp = None
        if attributes.get('llm.response.timestamp'):
            response_timestamp = datetime.fromisoformat(
                attributes.get('llm.response.timestamp').replace('Z', '+00:00')
            )
        
        # Create LLM interaction
        llm_interaction = cls(
            event_id=event.id,
            interaction_type=interaction_type,
            vendor=attributes.get('llm.vendor', ''),
            model=attributes.get('llm.model', ''),
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp,
            duration_ms=attributes.get('llm.response.duration_ms'),
            input_tokens=attributes.get('llm.usage.input_tokens'),
            output_tokens=attributes.get('llm.usage.output_tokens'),
            total_tokens=attributes.get('llm.usage.total_tokens'),
            request_data=attributes.get('llm.request.data'),
            response_content=attributes.get('llm.response.content'),
            response_id=attributes.get('llm.response.id'),
            stop_reason=attributes.get('llm.response.stop_reason')
        )
        
        db_session.add(llm_interaction)
        
        # Create attributes
        from src.models.llm_attribute import LLMAttribute
        for key, value in attributes.items():
            # Skip attributes that are already stored as columns
            if key.startswith('llm.') and key in [
                'llm.vendor', 'llm.model', 'llm.request.timestamp', 
                'llm.response.timestamp', 'llm.response.duration_ms',
                'llm.usage.input_tokens', 'llm.usage.output_tokens', 
                'llm.usage.total_tokens', 'llm.request.data',
                'llm.response.content', 'llm.response.id',
                'llm.response.stop_reason'
            ]:
                continue
                
            LLMAttribute.create_from_value(
                db_session, 
                llm_interaction.id, 
                key, 
                value
            )
        
        return llm_interaction
    
    def get_cost_estimate(self, input_price_per_1k: float = 0.0, output_price_per_1k: float = 0.0) -> float:
        """
        Calculate an estimated cost for this LLM interaction.
        
        Args:
            input_price_per_1k: Price per 1,000 input tokens
            output_price_per_1k: Price per 1,000 output tokens
            
        Returns:
            float: Estimated cost in the model's pricing currency
        """
        input_cost = (self.input_tokens or 0) * input_price_per_1k / 1000
        output_cost = (self.output_tokens or 0) * output_price_per_1k / 1000
        return input_cost + output_cost
    
    def get_request_content(self) -> List[str]:
        """
        Extract user messages from the request data.
        
        Returns:
            List[str]: User messages
        """
        if not self.request_data or not isinstance(self.request_data, dict):
            return []
            
        messages = self.request_data.get('messages', [])
        if not messages:
            return []
            
        results = []
        for message in messages:
            if message.get('role') == 'user':
                content = message.get('content', '')
                if isinstance(content, str):
                    results.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            results.append(item.get('text', ''))
        
        return results
    
    def get_response_content(self) -> List[str]:
        """
        Extract assistant responses from the response content.
        
        Returns:
            List[str]: Assistant responses
        """
        if not self.response_content:
            return []
            
        if isinstance(self.response_content, list):
            results = []
            for item in self.response_content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    results.append(item.get('text', ''))
            return results
        
        return [] 