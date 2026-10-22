import os
from pathlib import Path

# Resolve default SQLite path to backend/db.sql regardless of invocation directory
DEFAULT_DB_FILE = Path(__file__).resolve().parent.parent.parent / "db.sql"


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE}")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"


settings = Settings()
