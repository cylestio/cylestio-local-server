"""
Processing module for telemetry data.

This module provides the processing capabilities for the Cylestio Local Server,
handling telemetry events from various sources.
"""

# Import processors
from src.processing.simple_processor import SimpleProcessor, ProcessingError

# Define all classes that should be imported from this module
__all__ = ["SimpleProcessor", "ProcessingError"] 