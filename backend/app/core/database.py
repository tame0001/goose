from typing import Generator
from sqlalchemy import event
from sqlmodel import Session, create_engine
from app.core.config import settings

# Configure SQLite-specific connection arguments if using SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
        "timeout": 30.0,  # Wait up to 30 seconds if DB is busy before failing
    }

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.SQL_ECHO,
)

# Apply SQLite-specific optimizations (WAL mode and busy timeout)
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
