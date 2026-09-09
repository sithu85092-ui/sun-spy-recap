import os
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set."
    )

# Render may sometimes provide postgres://
# SQLAlchemy expects postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1,
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=2,
    max_overflow=3,
    connect_args={
        "connect_timeout": 10,
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def utcnow():
    return datetime.now(timezone.utc)


def init_db():
    # Import models before create_all()
    from backend.models import Job

    Base.metadata.create_all(
        bind=engine
    )

    print(
        "PostgreSQL database initialized successfully.",
        flush=True,
    )
