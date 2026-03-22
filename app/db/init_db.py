"""Database initialization helpers."""

from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine
from app.models.fire_alert import FireAlert  # noqa: F401


def init_db() -> None:
    """Ensure required extensions and tables exist."""

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
