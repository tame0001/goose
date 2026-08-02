from typing import Generator
from sqlmodel import Session, create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.SQL_ECHO,
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
