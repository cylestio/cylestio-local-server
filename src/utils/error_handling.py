"""
Error handling utilities for the processing layer.

This module provides error handling utilities for the processing layer,
including error formatters and logging helpers.
"""
import logging
import traceback
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime


# Set up logger
logger = logging.getLogger(__name__)


def format_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Format an error for logging or API responses.
    
    Args:
        error: The exception to format
        context: Additional context information
        include_traceback: Whether to include a traceback
        
    Returns:
        dict: Formatted error information
    """
    # Create basic error info
    error_info = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "timestamp": datetime.now().isoformat()
    }
    
    # Add traceback if requested
    if include_traceback:
        error_info["traceback"] = traceback.format_exc()
    
    # Add context if provided
    if context:
        error_info["context"] = context
    
    # Add additional fields from specialized errors
    if hasattr(error, "field"):
        error_info["field"] = getattr(error, "field")
    
    if hasattr(error, "details"):
        error_info["details"] = getattr(error, "details")
    
    return error_info


def log_processing_error(
    error: Exception,
    telemetry_data: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
):
    """
    Log a processing error with context.
    
    Args:
        error: The exception to log
        telemetry_data: The telemetry data being processed (if available)
        context: Additional context information
        level: Log level (error, warning, info, etc.)
    """
    # Format the error
    error_info = format_error(error, context, include_traceback=True)
    
    # Add telemetry data if available (redacted to avoid logging sensitive info)
    if telemetry_data:
        # Include only non-sensitive fields
        safe_fields = ["schema_version", "timestamp", "trace_id", "span_id", "name", "level", "agent_id"]
        safe_data = {k: v for k, v in telemetry_data.items() if k in safe_fields}
        
        # Add record identifier information
        if "name" in telemetry_data:
            error_info["record_type"] = telemetry_data["name"]
        
        if "agent_id" in telemetry_data:
            error_info["agent_id"] = telemetry_data["agent_id"]
        
        # Include safe data in context
        error_info["telemetry_data"] = safe_data
    
    # Log the error with the appropriate level
    log_message = f"Processing error: {error}"
    
    if level == "error":
        logger.error(log_message, extra={"error_info": error_info})
    elif level == "warning":
        logger.warning(log_message, extra={"error_info": error_info})
    elif level == "info":
        logger.info(log_message, extra={"error_info": error_info})
    else:
        # Default to error
        logger.error(log_message, extra={"error_info": error_info})


def format_processing_result(
    success_count: int,
    error_count: int,
    errors: List[Exception],
    processing_time_ms: int
) -> Dict[str, Any]:
    """
    Format processing results for API responses.
    
    Args:
        success_count: Number of successfully processed records
        error_count: Number of records that failed processing
        errors: List of errors encountered
        processing_time_ms: Processing time in milliseconds
        
    Returns:
        dict: Formatted processing results
    """
    # Format errors (without tracebacks for API responses)
    formatted_errors = [
        format_error(error, include_traceback=False)
        for error in errors[:10]  # Limit to first 10 errors
    ]
    
    # Create result info
    result_info = {
        "success_count": success_count,
        "error_count": error_count,
        "processing_time_ms": processing_time_ms,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add errors if any
    if error_count > 0:
        result_info["errors"] = formatted_errors
        
        # If there are more errors than we're showing
        if len(errors) > 10:
            result_info["error_truncated"] = True
            result_info["total_error_count"] = len(errors)
    
    return result_info 