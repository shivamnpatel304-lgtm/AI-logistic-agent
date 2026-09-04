"""
Database connection and session management.
Provides SQLAlchemy engine, Base declarative model, and database dependency.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# SQLite needs connect_args check_same_thread=False for multithreaded web servers
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG and False,  # set to True if deep query debugging needed
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a SQLAlchemy session per request
    and ensures it is closed when the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initializes database tables by importing all registered models
    and invoking metadata.create_all.
    """
    # Import all models here so that they are registered on the Base metadata
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
