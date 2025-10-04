from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.evaluation import Evaluation, EvaluationStatus


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: str, exclude_soft_deleted: bool = True) -> Optional[Evaluation]:
        filters = [Evaluation.id == id]
        if exclude_soft_deleted:
            filters.append(Evaluation.deleted_at.is_(None))
        return self.db.query(Evaluation).filter(*filters).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[EvaluationStatus] = None,
        exclude_soft_deleted: bool = True,
    ) -> List[Evaluation]:
        filters = []
        if status:
            filters.append(Evaluation.status == status)
        if exclude_soft_deleted:
            filters.append(Evaluation.deleted_at.is_(None))
        return (
            self.db.query(Evaluation).filter(*filters).offset(skip).limit(limit).all()
        )

    def create(self, obj_in: dict) -> Evaluation:
        db_obj = Evaluation(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, evaluation: Evaluation, obj_in: dict) -> Evaluation:
        for field, value in obj_in.items():
            setattr(evaluation, field, value)
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def delete(self, evaluation: Evaluation) -> bool:
        evaluation.deleted_at = datetime.now()
        self.db.commit()
        return True

    def update_status(
        self, evaluation: Evaluation, status: EvaluationStatus
    ) -> Evaluation:
        evaluation.status = status.value
        if status == EvaluationStatus.PROCESSING:
            evaluation.started_at = datetime.now()
        elif status in [EvaluationStatus.COMPLETED, EvaluationStatus.FAILED]:
            evaluation.completed_at = datetime.now()
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def update_failed_status(
        self, evaluation: Evaluation, error_message: str
    ) -> Evaluation:
        evaluation.status = EvaluationStatus.FAILED.value
        evaluation.error_message = error_message
        evaluation.retry_count += 1
        evaluation.completed_at = datetime.now()
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def save_results(self, evaluation: Evaluation, results: dict) -> Evaluation:
        evaluation.cv_match_rate = results.get("cv_match_rate")
        evaluation.cv_feedback = results.get("cv_feedback")
        evaluation.project_score = results.get("project_score")
        evaluation.project_feedback = results.get("project_feedback")
        evaluation.overall_summary = results.get("overall_summary")
        evaluation.cv_detailed_scores = results.get("cv_detailed_scores")
        evaluation.project_detailed_scores = results.get("project_detailed_scores")
        evaluation.status = EvaluationStatus.COMPLETED.value
        evaluation.completed_at = datetime.now()
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation
