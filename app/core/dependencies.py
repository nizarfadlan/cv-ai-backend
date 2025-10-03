from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.document import DocumentRepository
from app.repositories.evaluation import EvaluationRepository


def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_evaluation_repository(db: Session = Depends(get_db)) -> EvaluationRepository:
    return EvaluationRepository(db)
