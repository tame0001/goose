import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./db.sql")
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"


settings = Settings()
