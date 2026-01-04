"""
Database session management using SQLAlchemy.

This module provides database connection and session handling with proper
connection pooling and error handling.
"""

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create database engine
# echo=True logs all SQL queries (useful for debugging, disable in production)
engine = create_engine(
    DATABASE_URL,
    echo=True if os.getenv("ENVIRONMENT") == "development" else False,
    pool_pre_ping=True,  # Verify connections before using (handles dropped connections)
    pool_size=5,  # Number of connections to keep open
    max_overflow=10,  # Additional connections under high load
)

# Create session factory
# Sessions are how you interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session.

    Usage in FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()

    Yields:
        Database session that is automatically closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI.

    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
            print(user.name)

    Yields:
        Database session that is automatically closed
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
