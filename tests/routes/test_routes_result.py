from typing import Any, Dict
import pytest
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation, EvaluationStatus
from app.repositories.evaluation import EvaluationRepository


class TestResultRoutes:
    @pytest.fixture
    def uploaded_documents(
        self,
        client: TestClient,
        sample_cv_pdf_content: bytes,
        sample_project_pdf_content: bytes,
        temp_upload_dir,
    ):
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_project_pdf_content),
            "application/pdf",
        )

        response = client.post(
            "/upload/",
            files={"cv": cv_file, "project_report": project_file},
        )

        data = response.json()
        return {
            "cv_id": data["cv_document"]["id"],
            "project_id": data["project_document"]["id"],
        }

    @pytest.fixture
    def created_evaluation(
        self, db_session: Session, uploaded_documents: Dict[str, Any]
    ) -> Evaluation:
        eval_repo = EvaluationRepository(db_session)
        evaluation_data = {
            "job_title": "Backend Developer",
            "cv_document_id": uploaded_documents["cv_id"],
            "project_document_id": uploaded_documents["project_id"],
        }
        evaluation = eval_repo.create(evaluation_data)
        return evaluation

    def test_get_evaluation_queued_status(
        self, client: TestClient, created_evaluation: Evaluation
    ):
        response = client.get(f"/result/{created_evaluation.id}/")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(created_evaluation.id)
        assert data["status"] == "queued"
        assert "result" not in data or data["result"] is None

    def test_get_evaluation_processing_status(
        self, client: TestClient, created_evaluation: Evaluation, db_session: Session
    ):
        eval_repo = EvaluationRepository(db_session)
        eval_repo.update_status(created_evaluation, EvaluationStatus.PROCESSING)

        response = client.get(f"/result/{created_evaluation.id}/")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "processing"
        assert "result" not in data or data["result"] is None

    def test_get_evaluation_completed_status(
        self, client: TestClient, created_evaluation: Evaluation, db_session: Session
    ):
        eval_repo = EvaluationRepository(db_session)

        # Save mock results
        results = {
            "cv_match_rate": 0.82,
            "cv_feedback": "Strong technical skills",
            "project_score": 4.5,
            "project_feedback": "Well-implemented solution",
            "overall_summary": "Recommended candidate",
            "cv_detailed_scores": {
                "technical_skills": 4,
                "experience_level": 3,
                "achievements": 4,
                "cultural_fit": 5,
            },
            "project_detailed_scores": {
                "correctness": 4,
                "code_quality": 5,
                "resilience": 4,
                "documentation": 5,
                "creativity": 3,
            },
        }
        eval_repo.save_results(created_evaluation, results)

        response = client.get(f"/result/{created_evaluation.id}/")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["cv_match_rate"] == 0.82
        assert data["result"]["project_score"] == 4.5
        assert "cv_detailed_scores" in data["result"]
        assert "project_detailed_scores" in data["result"]

    def test_get_evaluation_failed_status(
        self, client: TestClient, created_evaluation: Evaluation, db_session: Session
    ):
        eval_repo = EvaluationRepository(db_session)
        eval_repo.update_failed_status(created_evaluation, "LLM API timeout")

        response = client.get(f"/result/{created_evaluation.id}/")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "failed"
        assert data["error_message"] == "LLM API timeout"

    def test_get_evaluation_not_found(self, client: TestClient):
        fake_id = "0199b3f8-2757-7bee-b682-df515eaff6b0"  # Non-existent ID
        response = client.get(f"/result/{fake_id}/")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_evaluation_invalid_uuid(self, client: TestClient):
        response = client.get("/result/invalid-uuid/")

        assert response.status_code == 422
