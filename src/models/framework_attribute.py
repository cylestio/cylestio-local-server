"""
Framework Attribute model and related functionality.

This module defines the FrameworkAttribute model that represents a key-value attribute
associated with a framework event.
"""
from typing import Any, Dict, List

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.models.attribute_base import AttributeBase


class FrameworkAttribute(AttributeBase):
    """
    FrameworkAttribute model representing key-value attributes for framework events.
    
    This model allows storing arbitrary metadata about framework events in a flexible
    key-value format with type information.
    """
    __tablename__ = "framework_attributes"
    
    framework_event_id = Column(
        Integer, 
        ForeignKey("framework_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Define parent id field name for the base class methods
    parent_id_field_name = "framework_event_id"
    
    # Relationship
    framework_event = relationship("FrameworkEvent", back_populates="attributes")
    
    def __repr__(self) -> str:
        return f"<FrameworkAttribute {self.id} {self.key}={self.value}>"
    
    @classmethod
    def create_framework_attributes(cls, db_session, framework_event_id: int, 
                                   attributes: Dict[str, Any]) -> List["FrameworkAttribute"]:
        """
        Create framework attribute records from a dictionary.
        
        Args:
            db_session: Database session
            framework_event_id: ID of the framework event
            attributes: Dictionary of attribute key-value pairs
            
        Returns:
            List of created framework attribute records
        """
        return cls.create_from_dict(db_session, framework_event_id, attributes)
    
    @classmethod
    def get_framework_attributes_dict(cls, db_session, framework_event_id: int) -> Dict[str, Any]:
        """
        Get all attributes for a framework event as a dictionary.
        
        Args:
            db_session: Database session
            framework_event_id: ID of the framework event
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        return cls.to_dict(db_session, framework_event_id) 