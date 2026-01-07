"""
Shared API dependencies.
"""

from typing import Generator
from sqlalchemy.orm import Session
from src.db.session import get_db


def get_database() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI."""
    yield from get_db()
