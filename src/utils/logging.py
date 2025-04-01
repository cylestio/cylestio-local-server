import logging
import sys
from typing import Dict, Any
from src.config.settings import get_settings

def configure_logging() -> None:
    """
    Configure application logging
    """
    settings = get_settings()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Log configuration
    logging.info(f"Logging configured with level {settings.LOG_LEVEL}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name
    """
    return logging.getLogger(name) 