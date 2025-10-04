from uuid import UUID
from pydantic import (
    UUID7,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from typing import Optional, Dict
from app.models.evaluation import EvaluationStatus


class EvaluationCreate(BaseModel):
    job_title: str = Field(..., min_length=1, max_length=255)
    cv_document_id: UUID7
    project_document_id: UUID7


class EvaluationResult(BaseModel):
    cv_match_rate: Optional[float] = None
    cv_feedback: Optional[str] = None
    project_score: Optional[float] = None
    project_feedback: Optional[str] = None
    overall_summary: Optional[str] = None
    cv_detailed_scores: Optional[Dict] = None
    project_detailed_scores: Optional[Dict] = None


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: EvaluationStatus
    error_message: Optional[str] = None
    result: Optional[EvaluationResult] = None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class EvaluationQueueResponse(BaseModel):
    id: str
    status: EvaluationStatus

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v
