from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

from app.core.config import settings

# SQLAlchemy setup for direct relational queries
engine_kwargs = {"pool_pre_ping": True}
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = getattr(settings, "DATABASE_POOL_SIZE", 10)
    engine_kwargs["max_overflow"] = getattr(settings, "DATABASE_MAX_OVERFLOW", 20)
    engine_kwargs["pool_timeout"] = getattr(settings, "DATABASE_POOL_TIMEOUT", 30)
    engine_kwargs["pool_recycle"] = getattr(settings, "DATABASE_POOL_RECYCLE", 1800)

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """
    FastAPI dependency yielding a SQLAlchemy DB session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_supabase_client() -> Client:
    """
    Returns a configured Supabase Client for Auth & Realtime operations.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
