import pytest
from io import BytesIO
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestEvaluateRoutes:
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

    @patch("app.workers.evaluation_worker.process_evaluation_task.delay")
    def test_create_evaluation_success(
        self, mock_celery_task, client: TestClient, uploaded_documents
    ):
        mock_celery_task.return_value = MagicMock(id="task-123")

        payload = {
            "job_title": "Backend Developer",
            "cv_document_id": uploaded_documents["cv_id"],
            "project_document_id": uploaded_documents["project_id"],
        }

        response = client.post("/evaluate/", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["status"] == "queued"

        # Verify Celery task was called
        mock_celery_task.assert_called_once()

    def test_create_evaluation_missing_cv_document(
        self, client: TestClient, uploaded_documents
    ):
        payload = {
            "job_title": "Backend Developer",
            "cv_document_id": "0199b3f8-2757-7bee-b682-df515eaff6b0",  # Non-existent ID
            "project_document_id": uploaded_documents["project_id"],
        }

        response = client.post("/evaluate/", json=payload)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_evaluation_missing_project_document(
        self, client: TestClient, uploaded_documents
    ):
        payload = {
            "job_title": "Backend Developer",
            "cv_document_id": uploaded_documents["cv_id"],
            "project_document_id": "0199b3f8-2757-7bee-b682-df515eaff6b0",  # Non-existent ID
        }

        response = client.post("/evaluate/", json=payload)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_evaluation_invalid_payload(self, client: TestClient):
        payload = {
            "job_title": "",  # Empty job title
            "cv_document_id": "invalid-uuid",
            "project_document_id": "invalid-uuid",
        }

        response = client.post("/evaluate/", json=payload)

        assert response.status_code == 422

    def test_create_evaluation_missing_fields(self, client: TestClient):
        payload = {"job_title": "Backend Developer"}

        response = client.post("/evaluate/", json=payload)

        assert response.status_code == 422
