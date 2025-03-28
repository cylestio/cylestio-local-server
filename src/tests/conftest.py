"""
Test fixtures for Cylestio Local Server.

This module contains pytest fixtures for setting up test databases and sessions.
"""
import os
import tempfile
import pytest
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.base import Base


@pytest.fixture(scope="session")
def db_engine():
    """
    Create a SQLite in-memory database engine for testing.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(db_engine):
    """
    Create all database tables for testing.
    """
    Base.metadata.create_all(db_engine)
    yield
    Base.metadata.drop_all(db_engine)


@pytest.fixture(scope="function")
def db_session(db_engine, db_tables):
    """
    Create a new database session for a test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db_session_factory(db_engine, db_tables):
    """
    Create a new database session factory for tests that need multiple sessions.
    """
    session_factory = sessionmaker(bind=db_engine)
    
    @contextmanager
    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    
    return get_session


@pytest.fixture(scope="function")
def temp_db_path():
    """
    Create a temporary file path for a SQLite database.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="function")
def temp_db_engine(temp_db_path):
    """
    Create a SQLite database engine with a temporary file.
    """
    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def temp_db_session(temp_db_engine):
    """
    Create a new database session for a test with a temporary file database.
    """
    connection = temp_db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close() 