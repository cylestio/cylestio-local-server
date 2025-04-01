from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from src.config.settings import get_settings

# Get settings
settings = get_settings()

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Session:
    """
    Get a database session
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    Initialize the database by creating all tables
    """
    # Import all models to ensure they are registered with Base
    # pylint: disable=import-outside-toplevel, unused-import
    from src.models.agent import Agent
    from src.models.session import Session
    from src.models.trace import Trace
    from src.models.span import Span
    from src.models.event import Event
    from src.models.llm_interaction import LLMInteraction
    from src.models.tool_interaction import ToolInteraction
    from src.models.security_alert import SecurityAlert
    from src.models.framework_event import FrameworkEvent
    
    # Create the tables
    Base.metadata.create_all(bind=engine) 