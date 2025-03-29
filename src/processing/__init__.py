"""
Processing package for the Cylestio Local Server.

This package handles event data processing, validation,
transformation, and storage.
"""

from processing.simple_processor import SimpleProcessor, ProcessingError

__all__ = ['SimpleProcessor', 'ProcessingError'] 