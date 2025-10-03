from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.evaluation import Evaluation, EvaluationStatus


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: str) -> Optional[Evaluation]:
        return self.db.query(Evaluation).filter(Evaluation.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Evaluation]:
        return self.db.query(Evaluation).offset(skip).limit(limit).all()

    def get_by_status(
        self, status: EvaluationStatus, skip: int = 0, limit: int = 100
    ) -> List[Evaluation]:
        return (
            self.db.query(Evaluation)
            .filter(Evaluation.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, obj_in: dict) -> Evaluation:
        db_obj = Evaluation(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Evaluation, obj_in: dict) -> Evaluation:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: str) -> bool:
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    def update_status(
        self, evaluation_id: str, status: EvaluationStatus
    ) -> Optional[Evaluation]:
        evaluation = self.get(evaluation_id)
        if evaluation:
            evaluation.status = status.value
            if status == EvaluationStatus.PROCESSING:
                evaluation.started_at = datetime.now()
            elif status in [EvaluationStatus.COMPLETED, EvaluationStatus.FAILED]:
                evaluation.completed_at = datetime.now()
            self.db.commit()
            self.db.refresh(evaluation)
        return evaluation

    def save_results(self, evaluation_id: str, results: dict) -> Optional[Evaluation]:
        evaluation = self.get(evaluation_id)
        if evaluation:
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
