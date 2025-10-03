from enum import StrEnum
from sqlalchemy import (
    UUID,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func
from app.database.base import Base
from uuid_extensions import uuid7 as generate_uuid7


class EvaluationStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuid7
    )
    job_title = Column(String, nullable=False)
    cv_document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    project_document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )

    status = Column(String, default=EvaluationStatus.QUEUED, nullable=False)

    cv_match_rate = Column(Float, nullable=True)
    cv_feedback = Column(Text, nullable=True)
    project_score = Column(Float, nullable=True)
    project_feedback = Column(Text, nullable=True)
    overall_summary = Column(Text, nullable=True)

    cv_detailed_scores = Column(JSON, nullable=True)
    project_detailed_scores = Column(JSON, nullable=True)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Evaluation(id={self.id}, status={self.status}, job_title={self.job_title})>"
