from sqlmodel import create_engine, Session

# Connect to the SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sql"  # Adjust the path as needed

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


def get_db():
    with Session(engine) as session:
        yield session
