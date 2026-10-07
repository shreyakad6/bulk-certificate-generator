import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-naive for SQLite & standard DB portability)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class CertificateStatus(str, Enum):
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"


class GenerationJob(Base):
    """Represents a bulk certificate generation batch job."""

    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.PENDING.value,
        index=True,
    )
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Certificate.created_at",
    )

    def __repr__(self) -> str:
        return f"<GenerationJob id={self.id} status={self.status} total={self.total_count}>"


class Certificate(Base):
    """Represents an individual certificate record belonging to a generation job."""

    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CertificateStatus.PENDING.value,
        index=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    # Relationships
    job: Mapped["GenerationJob"] = relationship(
        "GenerationJob",
        back_populates="certificates",
    )

    def __repr__(self) -> str:
        return f"<Certificate id={self.id} job_id={self.job_id} recipient={self.recipient_name} status={self.status}>"
