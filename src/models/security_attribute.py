"""
Security Attribute model and related functionality.

This module defines the SecurityAttribute model that represents a key-value attribute
associated with a security alert.
"""
from typing import Any, Dict, List

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.models.attribute_base import AttributeBase


class SecurityAttribute(AttributeBase):
    """
    SecurityAttribute model representing key-value attributes for security alerts.
    
    This model allows storing arbitrary metadata about security alerts in a flexible
    key-value format with type information.
    """
    __tablename__ = "security_attributes"
    
    security_alert_id = Column(
        Integer, 
        ForeignKey("security_alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Define parent id field name for the base class methods
    parent_id_field_name = "security_alert_id"
    
    # Relationship
    security_alert = relationship("SecurityAlert", back_populates="attributes")
    
    def __repr__(self) -> str:
        return f"<SecurityAttribute {self.id} {self.key}={self.value}>"
    
    @classmethod
    def create_security_attributes(cls, db_session, security_alert_id: int, 
                                  attributes: Dict[str, Any]) -> List["SecurityAttribute"]:
        """
        Create security attribute records from a dictionary.
        
        Args:
            db_session: Database session
            security_alert_id: ID of the security alert
            attributes: Dictionary of attribute key-value pairs
            
        Returns:
            List of created security attribute records
        """
        return cls.create_from_dict(db_session, security_alert_id, attributes)
    
    @classmethod
    def get_security_attributes_dict(cls, db_session, security_alert_id: int) -> Dict[str, Any]:
        """
        Get all attributes for a security alert as a dictionary.
        
        Args:
            db_session: Database session
            security_alert_id: ID of the security alert
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        return cls.to_dict(db_session, security_alert_id) 