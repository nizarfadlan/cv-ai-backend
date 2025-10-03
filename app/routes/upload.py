from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.schemas.document import UploadResponse, DocumentCreate, DocumentResponse
from app.repositories.document import DocumentRepository
from app.core.dependencies import get_document_repository
from app.utils.file_handler import save_upload_file
from app.models.document import DocumentType

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/", response_model=UploadResponse)
async def upload_documents(
    cv: UploadFile = File(..., description="Candidate CV (PDF)"),
    project_report: UploadFile = File(..., description="Project Report (PDF)"),
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
    try:
        # Save CV
        cv_filename, cv_path, cv_size = await save_upload_file(cv, "cv")
        cv_data = DocumentCreate(
            filename=cv_filename,
            original_filename=cv.filename,
            file_path=cv_path,
            file_size=cv_size,
            mime_type=cv.content_type,
            document_type=DocumentType.CV,
        )
        cv_document = doc_repo.create(cv_data.model_dump())

        # Save Project Report
        report_filename, report_path, report_size = await save_upload_file(
            project_report, "reports"
        )
        report_data = DocumentCreate(
            filename=report_filename,
            original_filename=project_report.filename,
            file_path=report_path,
            file_size=report_size,
            mime_type=project_report.content_type,
            document_type=DocumentType.PROJECT_REPORT,
        )
        report_document = doc_repo.create(report_data.model_dump())

        return UploadResponse(
            cv_document=DocumentResponse.model_validate(cv_document),
            project_document=DocumentResponse.model_validate(report_document),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
