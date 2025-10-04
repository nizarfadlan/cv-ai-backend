import asyncio
from celery import Celery
from app.config import settings
from app.database.session import SessionLocal
from app.repositories.document import DocumentRepository
from app.repositories.evaluation import EvaluationRepository
from app.services.evaluation_service import EvaluationService

celery_app = Celery(
    "evaluation_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="process_evaluation", bind=True, max_retries=3)
def process_evaluation_task(self, evaluation_id: str):
    db = SessionLocal()
    try:
        doc_repo = DocumentRepository(db)
        eval_repo = EvaluationRepository(db)

        evaluation_service = EvaluationService()
        results = asyncio.run(
            evaluation_service.process_evaluation(
                evaluation_id=evaluation_id,
                doc_repo=doc_repo,
                eval_repo=eval_repo,
            )
        )

        return {
            "evaluation_id": evaluation_id,
            "status": "completed",
            "results": results,
        }

    except Exception as e:
        try:
            self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            return {
                "evaluation_id": evaluation_id,
                "status": "failed",
                "error": str(e),
            }
    finally:
        db.close()
