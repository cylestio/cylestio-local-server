"""
Server module for the Cylestio Local Server package.

This file provides direct access to the server when installed as a package.
"""
import os
import sys
import importlib.util
import uvicorn

# Import src bridge module first to setup proper imports
from cylestio_local_server.src import *

# Now import modules from src
from src.api import create_api_app
from src.utils.logging import configure_logging, get_logger
from src.config.settings import get_settings
from src.database.session import init_db
from src.models.base import engine

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Create app
app = create_api_app()

def run_server(host="0.0.0.0", port=8000, db_path="cylestio.db", reload=False, debug=False):
    """
    Run the Cylestio Local Server.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        db_path: Path to the SQLite database file
        reload: Whether to enable auto-reload for development
        debug: Whether to enable debug mode
    """
    # Set environment variables for configuration
    os.environ["HOST"] = host
    os.environ["PORT"] = str(port)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DEBUG"] = str(debug).lower()
    
    # Initialize the database if needed
    try:
        print(f"Initializing database at: {db_path}")
        print("This may take a moment on first run...")
        init_db()
        print("Database initialization complete!")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        print(f"Error initializing database: {str(e)}")
        print("The server will start, but some features may not work correctly.")
    
    # Log startup information
    print(f"Starting Cylestio Local Server on {host}:{port}")
    print(f"Using database: {db_path}")
    print("API documentation: http://localhost:8000/docs")
    
    # Run the server with uvicorn
    uvicorn.run(
        "cylestio_local_server.server:app",
        host=host,
        port=port,
        reload=reload
    ) 