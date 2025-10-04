from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator
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

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class UploadResponse(BaseModel):
    cv_document: DocumentResponse
    project_document: DocumentResponse
