"""
LLM Attribute model and related functionality.

This module defines the LLMAttribute model for storing key-value attributes
specific to LLM interactions.
"""
import json
from typing import Dict, Any, Union

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class LLMAttribute(Base):
    """
    LLM Attribute model for storing key-value attributes specific to LLM interactions.
    
    This model stores attributes that are specific to LLM interactions in a
    flexible key-value structure.
    """
    __tablename__ = "llm_attributes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    llm_interaction_id = Column(Integer, ForeignKey("llm_interactions.id"), nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value_text = Column(Text)
    value_numeric = Column(Float)
    value_boolean = Column(Boolean)
    value_type = Column(String, nullable=False)  # 'text', 'numeric', 'boolean', 'json'
    
    # Relationships
    llm_interaction = relationship("LLMInteraction", back_populates="attributes")
    
    def __repr__(self) -> str:
        return f"<LLMAttribute {self.id} ({self.key})>"
    
    @classmethod
    def create_from_value(cls, db_session, llm_interaction_id: int, key: str, value: Any) -> "LLMAttribute":
        """
        Create an LLMAttribute from a key-value pair.
        
        Args:
            db_session: Database session
            llm_interaction_id: ID of the parent LLM interaction
            key: Attribute key
            value: Attribute value
            
        Returns:
            LLMAttribute: The created attribute
        """
        # Determine value type and store accordingly
        value_type = 'text'
        value_text = None
        value_numeric = None
        value_boolean = None
        
        if value is None:
            value_type = 'text'
            value_text = None
        elif isinstance(value, bool):
            value_type = 'boolean'
            value_boolean = value
        elif isinstance(value, (int, float)):
            value_type = 'numeric'
            value_numeric = float(value)
        elif isinstance(value, (dict, list)):
            value_type = 'json'
            value_text = json.dumps(value)
        else:
            value_type = 'text'
            value_text = str(value)
        
        # Create attribute
        attribute = cls(
            llm_interaction_id=llm_interaction_id,
            key=key,
            value_text=value_text,
            value_numeric=value_numeric,
            value_boolean=value_boolean,
            value_type=value_type
        )
        
        db_session.add(attribute)
        return attribute
    
    @property
    def value(self) -> Any:
        """
        Get the attribute value in its native type.
        
        Returns:
            The attribute value in its native type
        """
        if self.value_type == 'boolean':
            return self.value_boolean
        elif self.value_type == 'numeric':
            return self.value_numeric
        elif self.value_type == 'json':
            try:
                return json.loads(self.value_text) if self.value_text else None
            except (json.JSONDecodeError, TypeError):
                return None
        else:
            return self.value_text 