"""
Tool Attribute model and related functionality.

This module defines the ToolAttribute model that represents a key-value attribute
associated with a tool interaction.
"""
from typing import Any, Dict, List

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.models.attribute_base import AttributeBase


class ToolAttribute(AttributeBase):
    """
    ToolAttribute model representing key-value attributes for tool interactions.
    
    This model allows storing arbitrary metadata about tool interactions in a flexible
    key-value format with type information.
    """
    __tablename__ = "tool_attributes"
    
    tool_interaction_id = Column(
        Integer, 
        ForeignKey("tool_interactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Define parent id field name for the base class methods
    parent_id_field_name = "tool_interaction_id"
    
    # Relationship
    tool_interaction = relationship("ToolInteraction", back_populates="attributes")
    
    def __repr__(self) -> str:
        return f"<ToolAttribute {self.id} {self.key}={self.value}>"
    
    @classmethod
    def create_tool_attributes(cls, db_session, tool_interaction_id: int, 
                              attributes: Dict[str, Any]) -> List["ToolAttribute"]:
        """
        Create tool attribute records from a dictionary.
        
        Args:
            db_session: Database session
            tool_interaction_id: ID of the tool interaction
            attributes: Dictionary of attribute key-value pairs
            
        Returns:
            List of created tool attribute records
        """
        return cls.create_from_dict(db_session, tool_interaction_id, attributes)
    
    @classmethod
    def get_tool_attributes_dict(cls, db_session, tool_interaction_id: int) -> Dict[str, Any]:
        """
        Get all attributes for a tool interaction as a dictionary.
        
        Args:
            db_session: Database session
            tool_interaction_id: ID of the tool interaction
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        return cls.to_dict(db_session, tool_interaction_id) 