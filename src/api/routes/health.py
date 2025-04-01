from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import os

from src.database.session import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health", summary="Check API health")
async def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Check the health of the API and its dependencies.
    
    Returns:
        dict: Health status information
    """
    # Check database connection
    db_status = "healthy"
    db_error = None
    
    try:
        # Simple query to check database connection
        db.execute(text("SELECT 1")).first()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
        logger.error(f"Database health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    # Get start time from process info
    try:
        process_start_time = datetime.fromtimestamp(os.path.getctime("/proc/self"))
    except:
        # Fallback for non-Linux systems
        process_start_time = datetime.now()
    
    # Build health response
    health_info = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "uptime": str(datetime.now() - process_start_time),
        "dependencies": {
            "database": {
                "status": db_status,
                "error": db_error
            }
        }
    }
    
    return health_info 