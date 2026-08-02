from app.core.config import settings
from app.core.database import engine, get_db

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

__all__ = ["engine", "get_db", "SQLALCHEMY_DATABASE_URL"]
