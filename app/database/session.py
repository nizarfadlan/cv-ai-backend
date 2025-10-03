from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

username = settings.POSTGRESQL_USER
password = settings.POSTGRESQL_PASSWORD
host = settings.POSTGRESQL_HOST
port = settings.POSTGRESQL_PORT
database = settings.POSTGRESQL_DATABASE

engine = create_engine(
    f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}",
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=0,
    pool_timeout=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
