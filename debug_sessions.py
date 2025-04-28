import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import needed modules
from src.models.base import Base
from src.analysis.agent_analysis import get_agent_sessions
from src.analysis.types import TimeRangeParams, PaginationParams

# Connect to database
engine = create_engine('sqlite:///cylestio.db', echo=True)
Session = sessionmaker(bind=engine)
db = Session()

# Add event listener to log SQL queries
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(datetime.now())
    logger.info(f"SQL Query: {statement}")
    logger.info(f"Parameters: {parameters}")

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = datetime.now() - conn.info['query_start_time'].pop(-1)
    logger.info(f"Total Time: {total}")

# Query weather-agent sessions
logger.info("Querying sessions for weather-agent")
time_range = TimeRangeParams(
    start=datetime.now() - timedelta(days=30),
    end=datetime.now()
)
weather_sessions, weather_count = get_agent_sessions(
    db, 
    'weather-agent', 
    time_range, 
    {}, 
    PaginationParams(page=1, page_size=50)
)
logger.info(f"Found {weather_count} sessions for weather-agent")

# Query unknown-agent sessions
logger.info("Querying sessions for unknown-agent")
unknown_sessions, unknown_count = get_agent_sessions(
    db, 
    'unknown-agent', 
    time_range, 
    {}, 
    PaginationParams(page=1, page_size=50)
)
logger.info(f"Found {unknown_count} sessions for unknown-agent") 