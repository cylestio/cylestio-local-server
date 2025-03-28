"""
Base model for attribute models.

This module provides a base class for attribute models that can be used
to store attribute key-value pairs for various specialized events.
"""
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey

from src.models.base import Base


class AttributeBase(Base):
    """
    Base class for attribute models.
    
    Provides common functionality for storing key-value attributes with
    different value types (text, numeric, boolean).
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False, index=True)
    value_text = Column(String)
    value_numeric = Column(Float)
    value_boolean = Column(Boolean)
    value_type = Column(String, nullable=False)
    
    @property
    def value(self) -> Union[str, float, bool, None]:
        """
        Get the attribute value based on its type.
        
        Returns:
            The value of the appropriate type
        """
        if self.value_type == 'text':
            return self.value_text
        elif self.value_type == 'numeric':
            return self.value_numeric
        elif self.value_type == 'boolean':
            return self.value_boolean
        return None
    
    @classmethod
    def create_from_dict(cls, db_session, parent_id: int, attributes: Dict[str, Any]) -> List["AttributeBase"]:
        """
        Create attribute records from a dictionary of key-value pairs.
        
        Args:
            db_session: Database session
            parent_id: ID of the parent record
            attributes: Dictionary of attribute key-value pairs
            
        Returns:
            List of created attribute records
        """
        attr_objects = []
        
        for key, value in attributes.items():
            # Skip None values
            if value is None:
                continue
                
            # Determine the value type
            value_type = cls._determine_value_type(value)
            
            # Create a new attribute object
            attr = cls(
                key=key,
                value_type=value_type,
            )
            
            # Set the foreign key field
            setattr(attr, cls.parent_id_field_name, parent_id)
            
            # Set the appropriate value field
            if value_type == 'text':
                attr.value_text = str(value)
            elif value_type == 'numeric':
                attr.value_numeric = float(value)
            elif value_type == 'boolean':
                attr.value_boolean = bool(value)
                
            attr_objects.append(attr)
            
        if attr_objects:
            db_session.add_all(attr_objects)
            
        return attr_objects
    
    @staticmethod
    def _determine_value_type(value: Any) -> str:
        """
        Determine the type of a value.
        
        Args:
            value: The value to check
            
        Returns:
            String representing the value type ('text', 'numeric', or 'boolean')
        """
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, (int, float)):
            return 'numeric'
        else:
            return 'text'
    
    @classmethod
    def get_attribute(cls, db_session, parent_id: int, key: str) -> Optional["AttributeBase"]:
        """
        Get an attribute by parent ID and key.
        
        Args:
            db_session: Database session
            parent_id: ID of the parent record
            key: Attribute key
            
        Returns:
            The attribute record, or None if not found
        """
        parent_field = getattr(cls, cls.parent_id_field_name)
        return db_session.query(cls).filter(
            parent_field == parent_id,
            cls.key == key
        ).first()
    
    @classmethod
    def get_attributes(cls, db_session, parent_id: int) -> List["AttributeBase"]:
        """
        Get all attributes for a parent record.
        
        Args:
            db_session: Database session
            parent_id: ID of the parent record
            
        Returns:
            List of attribute records
        """
        parent_field = getattr(cls, cls.parent_id_field_name)
        return db_session.query(cls).filter(
            parent_field == parent_id
        ).all()
    
    @classmethod
    def to_dict(cls, db_session, parent_id: int) -> Dict[str, Any]:
        """
        Convert attributes to a dictionary.
        
        Args:
            db_session: Database session
            parent_id: ID of the parent record
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        attributes = cls.get_attributes(db_session, parent_id)
        return {attr.key: attr.value for attr in attributes} 