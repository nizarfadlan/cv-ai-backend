from fastapi import APIRouter, Depends, HTTPException
from app.schemas.evaluation import EvaluationCreate, EvaluationQueueResponse
from app.repositories.evaluation import EvaluationRepository
from app.repositories.document import DocumentRepository
from app.core.dependencies import get_evaluation_repository, get_document_repository
from app.core.exceptions import DocumentNotFoundException
from app.workers.evaluation_worker import process_evaluation_task

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("/", response_model=EvaluationQueueResponse)
async def create_evaluation(
    evaluation_data: EvaluationCreate,
    eval_repo: EvaluationRepository = Depends(get_evaluation_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
    try:
        cv_doc = doc_repo.get(str(evaluation_data.cv_document_id))
        if not cv_doc:
            raise DocumentNotFoundException(str(evaluation_data.cv_document_id))

        project_doc = doc_repo.get(str(evaluation_data.project_document_id))
        if not project_doc:
            raise DocumentNotFoundException(str(evaluation_data.project_document_id))

        evaluation = eval_repo.create(evaluation_data.model_dump())

        process_evaluation_task.delay(str(evaluation.id))

        return EvaluationQueueResponse(
            id=str(evaluation.id),
            status=evaluation.status,
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
