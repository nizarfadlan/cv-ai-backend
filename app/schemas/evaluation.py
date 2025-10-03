from pydantic import UUID7, BaseModel, ConfigDict, Field
from typing import Optional, Dict
from app.models.evaluation import EvaluationStatus


class EvaluationCreate(BaseModel):
    job_title: str = Field(..., min_length=1, max_length=255)
    cv_document_id: UUID7
    project_document_id: UUID7


class EvaluationResult(BaseModel):
    cv_match_rate: float
    cv_feedback: str
    project_score: float
    project_feedback: str
    overall_summary: str
    cv_detailed_scores: Optional[Dict] = None
    project_detailed_scores: Optional[Dict] = None


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: EvaluationStatus
    result: Optional[EvaluationResult] = None


class EvaluationQueueResponse(BaseModel):
    id: str
    status: EvaluationStatus
