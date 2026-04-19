import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from db import Base

class JobStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"

class Job(Base):
    __tablename__ = "jobs"

    id:         Mapped[str]        = mapped_column(String(36), primary_key=True)
    filename:   Mapped[str]        = mapped_column(String(255))
    file_type:  Mapped[str]        = mapped_column(String(10))
    status:     Mapped[JobStatus]  = mapped_column(SAEnum(JobStatus), default=JobStatus.PENDING)
    result:     Mapped[str | None] = mapped_column(Text, nullable=True)
    error:      Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
