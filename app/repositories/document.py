from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentType


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Document]:
        return self.db.query(Document).offset(skip).limit(limit).all()

    def get_by_type(
        self, document_type: DocumentType, skip: int = 0, limit: int = 100
    ) -> List[Document]:
        return (
            self.db.query(Document)
            .filter(Document.document_type == document_type)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_filename(self, filename: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.filename == filename).first()

    def create(self, obj_in: dict) -> Document:
        db_obj = Document(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: Document, obj_in: dict) -> Document:
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
