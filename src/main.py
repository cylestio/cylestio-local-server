import uvicorn
import sys
from fastapi import FastAPI
from src.api import create_api_app
from src.utils.logging import configure_logging, get_logger
from src.config.settings import get_settings
from src.models.base import init_db, create_all, DATABASE_URL

# Configure logging first
configure_logging()

# Create logger
logger = get_logger(__name__)

# Create app
app = create_api_app()

@app.on_event("startup")
async def startup_event():
    """
    Initialize the database and other services on application startup.
    """
    logger.info("Starting Cylestio Local Server API")
    logger.info(f"Using database: {DATABASE_URL}")
    
    try:
        # Initialize database and create tables if needed
        logger.info("Initializing database and creating tables...")
        init_db()
        logger.info("Database initialization successful!")
    except Exception as e:
        logger.critical(f"Fatal error during database initialization: {e}", exc_info=True)
        logger.critical("Application cannot start due to database initialization failure")
        # Exit the application if database initialization fails
        # This is preferred over continuing with a broken database
        sys.exit(1)
    
    logger.info("Cylestio Local Server API started successfully")
    
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup resources on shutdown
    """
    logger.info("Shutting down Cylestio Local Server API")
    
if __name__ == "__main__":
    settings = get_settings()
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "src.main:app", 
        host=settings.HOST, 
        port=settings.PORT,
        reload=settings.DEBUG
    ) 