from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.document import DocumentType


class DocumentBase(BaseModel):
    filename: str
    document_type: DocumentType


class DocumentCreate(DocumentBase):
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    file_size: int
    uploaded_at: datetime


class UploadResponse(BaseModel):
    cv_document: DocumentResponse
    project_document: DocumentResponse
