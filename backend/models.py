from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from .database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(
        String(100),
        primary_key=True,
        index=True,
    )

    upload_id = Column(
        String(100),
        nullable=True,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="QUEUED",
        index=True,
    )

    progress = Column(
        Integer,
        nullable=False,
        default=0,
    )

    message = Column(
        Text,
        nullable=True,
    )

    input_file = Column(
        String(500),
        nullable=True,
    )

    output_file = Column(
        String(500),
        nullable=True,
    )

    error = Column(
        Text,
        nullable=True,
    )

    recap_text = Column(
        Text,
        nullable=True,
    )

    language = Column(
        String(20),
        nullable=True,
        default="my",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
