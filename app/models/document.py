from enum import StrEnum
from sqlalchemy import UUID, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.base import Base
from uuid_extensions import uuid7 as generate_uuid7


class DocumentType(StrEnum):
    CV = "cv"
    PROJECT_REPORT = "project_report"
    JOB_DESCRIPTION = "job_description"
    CASE_STUDY_BRIEF = "case_study_brief"
    SCORING_RUBRIC = "scoring_rubric"


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=generate_uuid7
    )
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, type={self.document_type}, filename={self.filename})>"
