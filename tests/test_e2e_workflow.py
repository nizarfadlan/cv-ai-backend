import pytest
from io import BytesIO
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationStatus
from app.repositories.evaluation import EvaluationRepository


class TestEndToEndWorkflow:
    @pytest.mark.asyncio
    @patch("app.workers.evaluation_worker.process_evaluation_task.delay")
    @patch("app.utils.pdf_parser.extract_text_from_pdf")
    async def test_complete_evaluation_workflow(
        self,
        mock_extract_pdf,
        mock_celery_task,
        client: TestClient,
        sample_cv_pdf_content: bytes,
        sample_project_pdf_content: bytes,
        temp_upload_dir,
        db_session: Session,
    ):
        # Step 1: Upload documents
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_project_pdf_content),
            "application/pdf",
        )

        upload_response = client.post(
            "/upload/", files={"cv": cv_file, "project_report": project_file}
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()

        cv_id = upload_data["cv_document"]["id"]
        project_id = upload_data["project_document"]["id"]

        # Step 2: Create evaluation
        mock_celery_task.return_value = MagicMock(id="task-123")

        eval_payload = {
            "job_title": "Backend Developer",
            "cv_document_id": cv_id,
            "project_document_id": project_id,
        }

        eval_response = client.post("/evaluate/", json=eval_payload)

        assert eval_response.status_code == 200
        eval_data = eval_response.json()

        evaluation_id = eval_data["id"]
        assert eval_data["status"] == "queued"

        # Step 3: Check queued status
        result_response = client.get(f"/result/{evaluation_id}/")
        assert result_response.status_code == 200
        assert result_response.json()["status"] == "queued"

        # Step 4: Simulate processing (update status)
        eval_repo = EvaluationRepository(db_session)
        evaluation = eval_repo.get(evaluation_id)
        eval_repo.update_status(evaluation, EvaluationStatus.PROCESSING)

        result_response = client.get(f"/result/{evaluation_id}/")
        assert result_response.json()["status"] == "processing"

        # Step 5: Simulate completion
        results = {
            "cv_match_rate": 0.85,
            "cv_feedback": "Excellent technical skills",
            "project_score": 4.7,
            "project_feedback": "Outstanding implementation",
            "overall_summary": "Highly recommended candidate",
            "cv_detailed_scores": {
                "technical_skills": 5,
                "experience_level": 4,
                "achievements": 4,
                "cultural_fit": 5,
            },
            "project_detailed_scores": {
                "correctness": 5,
                "code_quality": 5,
                "resilience": 4,
                "documentation": 5,
                "creativity": 4,
            },
        }

        eval_repo.save_results(evaluation, results)

        # Step 6: Get final results
        final_response = client.get(f"/result/{evaluation_id}/")
        assert final_response.status_code == 200

        final_data = final_response.json()
        assert final_data["status"] == "completed"
        assert final_data["result"]["cv_match_rate"] == 0.85
        assert final_data["result"]["project_score"] == 4.7

    @patch("app.workers.evaluation_worker.process_evaluation_task.delay")
    def test_workflow_with_invalid_documents(
        self,
        mock_celery_task,
        client: TestClient,
        sample_cv_pdf_content: bytes,
        sample_project_pdf_content: bytes,
        temp_upload_dir,
    ):
        # Upload valid documents
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_project_pdf_content),
            "application/pdf",
        )

        upload_response = client.post(
            "/upload/", files={"cv": cv_file, "project_report": project_file}
        )

        cv_id = upload_response.json()["cv_document"]["id"]

        # Try to create evaluation with invalid project ID
        eval_payload = {
            "job_title": "Backend Developer",
            "cv_document_id": cv_id,
            "project_document_id": "00000000-0000-0000-0000-000000000000",
        }

        eval_response = client.post("/evaluate/", json=eval_payload)
        assert eval_response.status_code == 404

    @patch("app.workers.evaluation_worker.process_evaluation_task.delay")
    def test_workflow_multiple_evaluations(
        self,
        mock_celery_task,
        client: TestClient,
        sample_cv_pdf_content: bytes,
        sample_project_pdf_content: bytes,
        temp_upload_dir,
    ):
        """Test creating multiple evaluations for same documents"""

        # Upload documents
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_project_pdf_content),
            "application/pdf",
        )

        upload_response = client.post(
            "/upload/", files={"cv": cv_file, "project_report": project_file}
        )

        cv_id = upload_response.json()["cv_document"]["id"]
        project_id = upload_response.json()["project_document"]["id"]

        mock_celery_task.return_value = MagicMock(id="task-123")

        # Create first evaluation
        eval_payload_1 = {
            "job_title": "Backend Developer",
            "cv_document_id": cv_id,
            "project_document_id": project_id,
        }

        eval_response_1 = client.post("/evaluate/", json=eval_payload_1)
        assert eval_response_1.status_code == 200
        eval_id_1 = eval_response_1.json()["id"]

        # Create second evaluation with different job title
        eval_payload_2 = {
            "job_title": "Senior Backend Developer",
            "cv_document_id": cv_id,
            "project_document_id": project_id,
        }

        eval_response_2 = client.post("/evaluate/", json=eval_payload_2)
        assert eval_response_2.status_code == 200
        eval_id_2 = eval_response_2.json()["id"]

        # Verify both evaluations exist
        assert eval_id_1 != eval_id_2

        result_1 = client.get(f"/result/{eval_id_1}/")
        result_2 = client.get(f"/result/{eval_id_2}/")

        assert result_1.status_code == 200
        assert result_2.status_code == 200

    def test_workflow_upload_errors(self, client: TestClient):
        # Test with wrong file type
        cv_file = ("cv.txt", BytesIO(b"text content"), "text/plain")
        project_file = ("project.pdf", BytesIO(b"pdf content"), "application/pdf")

        response = client.post(
            "/upload/", files={"cv": cv_file, "project_report": project_file}
        )
        assert response.status_code == 415

        # Test with missing file
        response = client.post("/upload/", files={"cv": cv_file})
        assert response.status_code == 422

    @patch("app.workers.evaluation_worker.process_evaluation_task.delay")
    def test_workflow_evaluation_failure(
        self,
        mock_celery_task,
        client: TestClient,
        sample_cv_pdf_content: bytes,
        sample_project_pdf_content: bytes,
        temp_upload_dir,
        db_session: Session,
    ):
        # Upload documents
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_project_pdf_content),
            "application/pdf",
        )

        upload_response = client.post(
            "/upload/", files={"cv": cv_file, "project_report": project_file}
        )

        cv_id = upload_response.json()["cv_document"]["id"]
        project_id = upload_response.json()["project_document"]["id"]

        # Create evaluation
        mock_celery_task.return_value = MagicMock(id="task-456")

        eval_payload = {
            "job_title": "Backend Developer",
            "cv_document_id": cv_id,
            "project_document_id": project_id,
        }

        eval_response = client.post("/evaluate/", json=eval_payload)
        evaluation_id = eval_response.json()["id"]

        # Simulate failure
        eval_repo = EvaluationRepository(db_session)
        evaluation = eval_repo.get(evaluation_id)
        eval_repo.update_failed_status(evaluation, "LLM API timeout")

        # Check failed status
        result_response = client.get(f"/result/{evaluation_id}/")
        result_data = result_response.json()

        assert result_data["status"] == "failed"
        assert result_data["error_message"] == "LLM API timeout"
        assert "result" not in result_data or result_data["result"] is None
