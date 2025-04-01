import uvicorn
from src.api import create_api_app
from src.utils.logging import configure_logging, get_logger
from src.config.settings import get_settings
from src.database.session import init_db

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
    init_db()  # Make sure we create all the database tables
    # Additional startup tasks can be added here
    
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
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