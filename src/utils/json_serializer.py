"""
JSON serialization utilities.

This module provides utilities for JSON serialization, including
a custom encoder that can handle datetime objects and other 
non-standard JSON types.
"""

import json
from datetime import datetime, date
from typing import Any


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle datetime and date objects.
    
    This encoder converts datetime and date objects to ISO format strings,
    which can be serialized to JSON.
    """
    
    def default(self, obj: Any) -> Any:
        """
        Convert object to a JSON-serializable type.
        
        Args:
            obj: The object to convert
            
        Returns:
            A JSON-serializable representation of the object
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # Let the parent class handle other types or raise TypeError
        return super().default(obj)


def dumps(obj: Any, **kwargs) -> str:
    """
    Serialize object to a JSON string using the custom encoder.
    
    Args:
        obj: The object to serialize
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        str: The JSON string
    """
    return json.dumps(obj, cls=DateTimeEncoder, **kwargs)


def loads(s: str, **kwargs) -> Any:
    """
    Deserialize JSON string to an object.
    
    Args:
        s: The JSON string to deserialize
        **kwargs: Additional arguments to pass to json.loads
        
    Returns:
        Any: The deserialized object
    """
    return json.loads(s, **kwargs) 