from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentType


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: str, exclude_soft_deleted: bool = True) -> Optional[Document]:
        filters = [Document.id == id]
        if exclude_soft_deleted:
            filters.append(Document.deleted_at.is_(None))
        return self.db.query(Document).filter(*filters).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        document_type: Optional[DocumentType] = None,
        exclude_soft_deleted: bool = True,
    ) -> List[Document]:
        filters = []
        if document_type:
            filters.append(Document.document_type == document_type)
        if exclude_soft_deleted:
            filters.append(Document.deleted_at.is_(None))
        return self.db.query(Document).filter(*filters).offset(skip).limit(limit).all()

    def get_by_filename(
        self, filename: str, exclude_soft_deleted: bool = True
    ) -> Optional[Document]:
        filters = [Document.filename == filename]
        if exclude_soft_deleted:
            filters.append(Document.deleted_at.is_(None))
        return self.db.query(Document).filter(*filters).first()

    def create(self, obj_in: dict) -> Document:
        db_obj = Document(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, document: Document, obj_in: dict) -> Document:
        for field, value in obj_in.items():
            setattr(document, field, value)
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document: Document) -> bool:
        document.deleted_at = datetime.now()
        self.db.commit()
        return True
