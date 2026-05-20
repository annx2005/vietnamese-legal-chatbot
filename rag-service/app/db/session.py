from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

def _database_url():
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    if settings.CLOUD_SQL_CONNECTION_NAME:
        return URL.create(
            "postgresql+psycopg2",
            username=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            query={"host": f"/cloudsql/{settings.CLOUD_SQL_CONNECTION_NAME}"},
        )
    return URL.create(
        "postgresql+psycopg2",
        username=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )


engine = create_engine(_database_url(), pool_pre_ping=True, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
