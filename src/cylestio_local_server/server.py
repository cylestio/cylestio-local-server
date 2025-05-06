"""
Server module for the Cylestio Local Server package.

This file provides direct access to the server when installed as a package.
"""
import os
import sys
import importlib.util
import uvicorn
import pathlib

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
    
    # Ensure we use the correct database path
    database_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["DEBUG"] = str(debug).lower()
    
    # Force the import to use the new value by updating the imported constants
    # This step is crucial because some modules cache the values at import time
    import src.models.base
    src.models.base.DATABASE_URL = database_url
    src.models.base.engine = src.models.base.create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
        json_serializer=src.models.base.dumps,
        json_deserializer=src.models.base.loads
    )
    src.models.base.SessionLocal = src.models.base.sessionmaker(
        autocommit=False, autoflush=False, bind=src.models.base.engine
    )
    
    # Check if database already exists
    db_file = pathlib.Path(db_path)
    is_new_db = not db_file.exists()
    
    # Initialize the database if needed
    try:
        if is_new_db:
            print(f"Creating new database at: {db_path}")
            print("This may take a moment...")
        else:
            print(f"Using existing database at: {db_path}")
            print("Checking for required tables...")
            
        init_db()
        
        if is_new_db:
            print("✅ Database created successfully!")
        else:
            print("✅ Database checks completed successfully!")
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        print(f"Error initializing database: {str(e)}")
        print("The server will start, but some features may not work correctly.")
    
    # Log startup information
    print(f"Starting Cylestio Local Server on {host}:{port}")
    print(f"Using database: {db_path}")
    print(f"API documentation: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs")
    
    # Run the server with uvicorn
    uvicorn.run(
        "cylestio_local_server.server:app",
        host=host,
        port=port,
        reload=reload
    ) 