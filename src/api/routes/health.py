from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from datetime import datetime
import os

from src.database.session import get_db, engine
from src.utils.logging import get_logger
from src.models.agent import Agent

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health", summary="Check API health")
async def health_check(response: Response, db: Session = Depends(get_db)):
    """
    Check the health of the API and its dependencies.
    
    Returns:
        dict: Health status information
    """
    # Check database connection and tables
    db_status = "healthy"
    db_error = None
    tables_status = "healthy"
    tables_error = None
    references_status = "healthy"
    references_error = None
    
    try:
        # Simple query to check database connection
        db.execute(text("SELECT 1")).first()
        
        # Check if all required tables exist
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # Required core tables for the application to function
        required_tables = {"agents", "events", "sessions", "traces", "spans"}
        
        # Check if all required tables exist
        missing_tables = required_tables - existing_tables
        
        if missing_tables:
            tables_status = "unhealthy"
            tables_error = f"Missing required tables: {', '.join(missing_tables)}"
            logger.error(f"Health check: {tables_error}")
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
        # If tables exist, test agent/session relationship
        if "agents" in existing_tables and "sessions" in existing_tables:
            try:
                # Create a test agent if none exists
                test_agent = db.query(Agent).first()
                if not test_agent:
                    logger.info("Health check: Creating test agent to verify database relationships")
                    test_agent = Agent(
                        agent_id="health-check-agent",
                        name="Health Check Agent",
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow(),
                        is_active=True
                    )
                    db.add(test_agent)
                    db.commit()
                
                # Test the agent/session reference
                test_query = """
                SELECT a.agent_id, COUNT(s.id) as session_count
                FROM agents a
                LEFT JOIN sessions s ON a.agent_id = s.agent_id
                GROUP BY a.agent_id
                LIMIT 1
                """
                db.execute(text(test_query)).first()
                logger.debug("Health check: Agent/session relationship test passed")
            except Exception as e:
                references_status = "unhealthy"
                references_error = f"Database reference check failed: {str(e)}"
                logger.error(f"Health check: {references_error}")
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            
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
        "status": "healthy" if (db_status == "healthy" and tables_status == "healthy" and references_status == "healthy") else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "uptime": str(datetime.now() - process_start_time),
        "dependencies": {
            "database": {
                "status": db_status,
                "error": db_error
            },
            "tables": {
                "status": tables_status,
                "error": tables_error
            },
            "references": {
                "status": references_status,
                "error": references_error
            }
        }
    }
    
    return health_info 