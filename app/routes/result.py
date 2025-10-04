from fastapi import APIRouter, Depends, Path
from pydantic import UUID7
from app.schemas.evaluation import EvaluationResponse, EvaluationResult
from app.repositories.evaluation import EvaluationRepository
from app.core.dependencies import get_evaluation_repository
from app.core.exceptions import EvaluationNotFoundException
from app.models.evaluation import EvaluationStatus

router = APIRouter(prefix="/result", tags=["result"])


@router.get("/{id}/", response_model=EvaluationResponse)
async def get_evaluation_result(
    id: UUID7 = Path(..., description="Evaluation ID"),
    eval_repo: EvaluationRepository = Depends(get_evaluation_repository),
):
    evaluation = eval_repo.get(str(id))
    if not evaluation:
        raise EvaluationNotFoundException(str(id))

    response = EvaluationResponse(
        id=str(evaluation.id),
        status=evaluation.status,
    )

    if evaluation.status == EvaluationStatus.FAILED.value:
        response.error_message = evaluation.error_message

    if evaluation.status == EvaluationStatus.COMPLETED.value:
        response.result = EvaluationResult(
            cv_match_rate=evaluation.cv_match_rate,
            cv_feedback=evaluation.cv_feedback,
            project_score=evaluation.project_score,
            project_feedback=evaluation.project_feedback,
            overall_summary=evaluation.overall_summary,
            cv_detailed_scores=evaluation.cv_detailed_scores,
            project_detailed_scores=evaluation.project_detailed_scores,
        )

    return response
