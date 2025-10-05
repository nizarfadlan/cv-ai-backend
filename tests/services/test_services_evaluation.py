import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentType
from app.services.evaluation_service import EvaluationService
from app.repositories.document import DocumentRepository
from app.repositories.evaluation import EvaluationRepository
from app.models.evaluation import EvaluationStatus


class TestEvaluationService:
    @pytest.fixture
    def evaluation_service(self):
        with patch("app.services.evaluation_service.RAGService"):
            service = EvaluationService()
            return service

    @pytest.fixture
    def mock_documents(self, db_session: Session):
        cv_doc = Document(
            filename="test_cv.pdf",
            original_filename="cv.pdf",
            file_path="/tmp/cv.pdf",
            file_size=1024,
            mime_type="application/pdf",
            document_type=DocumentType.CV,
        )
        db_session.add(cv_doc)

        project_doc = Document(
            filename="test_project.pdf",
            original_filename="project.pdf",
            file_path="/tmp/project.pdf",
            file_size=2048,
            mime_type="application/pdf",
            document_type=DocumentType.PROJECT_REPORT,
        )
        db_session.add(project_doc)
        db_session.commit()
        db_session.refresh(cv_doc)
        db_session.refresh(project_doc)

        return {"cv": cv_doc, "project": project_doc}

    @pytest.fixture
    def mock_evaluation(self, db_session: Session, mock_documents):
        eval_repo = EvaluationRepository(db_session)
        evaluation = eval_repo.create(
            {
                "job_title": "Backend Developer",
                "cv_document_id": str(mock_documents["cv"].id),
                "project_document_id": str(mock_documents["project"].id),
            }
        )
        return evaluation

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service.extract_text_from_pdf")
    async def test_process_evaluation_success(
        self,
        mock_extract_pdf,
        evaluation_service,
        mock_evaluation,
        mock_documents,
        db_session: Session,
    ):
        # Mock PDF extraction
        mock_extract_pdf.side_effect = ["CV text content", "Project report content"]

        # Mock RAG service
        evaluation_service.rag_service.retrieve_context = MagicMock(
            return_value="Retrieved context"
        )

        # Mock LLM service responses
        cv_eval_response = {
            "technical_skills_score": 4,
            "experience_level_score": 3,
            "achievements_score": 4,
            "cultural_fit_score": 5,
            "cv_match_rate": 0.82,
            "feedback": "Strong technical background",
        }

        project_eval_response = {
            "correctness_score": 4,
            "code_quality_score": 5,
            "resilience_score": 4,
            "documentation_score": 5,
            "creativity_score": 3,
            "project_score": 4.5,
            "feedback": "Well-implemented solution",
        }

        summary_response = "Recommended candidate with strong skills"

        with patch.object(
            evaluation_service.llm_service, "evaluate_cv", new_callable=AsyncMock
        ) as mock_eval_cv:
            mock_eval_cv.return_value = cv_eval_response

            with patch.object(
                evaluation_service.llm_service,
                "evaluate_project",
                new_callable=AsyncMock,
            ) as mock_eval_project:
                mock_eval_project.return_value = project_eval_response

                with patch.object(
                    evaluation_service.llm_service,
                    "synthesize_summary",
                    new_callable=AsyncMock,
                ) as mock_synthesize:
                    mock_synthesize.return_value = summary_response

                    doc_repo = DocumentRepository(db_session)
                    eval_repo = EvaluationRepository(db_session)

                    # Process evaluation
                    results = await evaluation_service.process_evaluation(
                        evaluation_id=str(mock_evaluation.id),
                        doc_repo=doc_repo,
                        eval_repo=eval_repo,
                    )

                    # Verify results
                    assert results["cv_match_rate"] == 0.82
                    assert results["project_score"] == 4.5
                    assert results["overall_summary"] == summary_response

                    # Verify evaluation status updated
                    db_session.refresh(mock_evaluation)
                    assert mock_evaluation.status == EvaluationStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_process_evaluation_not_found(
        self, evaluation_service, db_session: Session
    ):
        doc_repo = DocumentRepository(db_session)
        eval_repo = EvaluationRepository(db_session)

        with pytest.raises(ValueError, match="not found"):
            await evaluation_service.process_evaluation(
                evaluation_id="0199b3f8-2757-7bee-b682-df515eaff6b0",  # Non-existent ID
                doc_repo=doc_repo,
                eval_repo=eval_repo,
            )

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service.extract_text_from_pdf")
    async def test_process_evaluation_pdf_extraction_fails(
        self, mock_extract_pdf, evaluation_service, mock_evaluation, db_session: Session
    ):
        # Mock PDF extraction to return None
        mock_extract_pdf.return_value = None

        doc_repo = DocumentRepository(db_session)
        eval_repo = EvaluationRepository(db_session)

        with pytest.raises(ValueError, match="Failed to extract text"):
            await evaluation_service.process_evaluation(
                evaluation_id=str(mock_evaluation.id),
                doc_repo=doc_repo,
                eval_repo=eval_repo,
            )

        # Verify status updated to failed
        db_session.refresh(mock_evaluation)
        assert mock_evaluation.status == EvaluationStatus.FAILED.value

    @pytest.mark.asyncio
    @patch("app.services.evaluation_service.extract_text_from_pdf")
    async def test_process_evaluation_llm_error(
        self, mock_extract_pdf, evaluation_service, mock_evaluation, db_session: Session
    ):
        mock_extract_pdf.side_effect = ["CV text", "Project text"]

        evaluation_service.rag_service.retrieve_context = MagicMock(
            return_value="Context"
        )

        # Mock LLM service to raise exception
        with patch.object(
            evaluation_service.llm_service, "evaluate_cv", new_callable=AsyncMock
        ) as mock_eval_cv:
            mock_eval_cv.side_effect = Exception("LLM API error")

            doc_repo = DocumentRepository(db_session)
            eval_repo = EvaluationRepository(db_session)

            with pytest.raises(Exception, match="LLM API error"):
                await evaluation_service.process_evaluation(
                    evaluation_id=str(mock_evaluation.id),
                    doc_repo=doc_repo,
                    eval_repo=eval_repo,
                )

            # Verify status updated to failed
            db_session.refresh(mock_evaluation)
            assert mock_evaluation.status == EvaluationStatus.FAILED.value
            assert "LLM API error" in mock_evaluation.error_message
