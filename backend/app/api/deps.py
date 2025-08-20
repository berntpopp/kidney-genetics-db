"""
API dependencies
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db

def get_current_db() -> Generator[Session, None, None]:
    """Get database session dependency"""
    return get_db()
