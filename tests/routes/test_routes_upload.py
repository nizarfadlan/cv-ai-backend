from io import BytesIO
from pathlib import Path
from fastapi.testclient import TestClient


class TestUploadRoutes:
    def test_upload_documents_success(
        self, client: TestClient, sample_cv_pdf_content: bytes, temp_upload_dir
    ):
        # Prepare files
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_cv_pdf_content),
            "application/pdf",
        )

        # Upload
        response = client.post(
            "/upload/",
            files={"cv": cv_file, "project_report": project_file},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert "cv_document" in data
        assert "project_document" in data

        assert "id" in data["cv_document"]
        assert data["cv_document"]["document_type"] == "cv"

        assert "id" in data["project_document"]
        assert data["project_document"]["document_type"] == "project_report"

    def test_upload_missing_cv(self, client: TestClient, sample_cv_pdf_content: bytes):
        project_file = (
            "project.pdf",
            BytesIO(sample_cv_pdf_content),
            "application/pdf",
        )

        response = client.post(
            "/upload/",
            files={"project_report": project_file},
        )

        assert response.status_code == 422

    def test_upload_missing_project(
        self, client: TestClient, sample_cv_pdf_content: bytes
    ):
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")

        response = client.post(
            "/upload/",
            files={"cv": cv_file},
        )

        assert response.status_code == 422

    def test_upload_invalid_file_type(self, client: TestClient):
        cv_file = ("cv.txt", BytesIO(b"not a pdf"), "text/plain")
        project_file = ("project.pdf", BytesIO(b"also not a pdf"), "application/pdf")

        response = client.post(
            "/upload/",
            files={"cv": cv_file, "project_report": project_file},
        )

        assert response.status_code == 415
        assert "not supported" in response.json()["detail"].lower()

    def test_upload_file_too_large(self, client: TestClient, temp_upload_dir):
        # Create a file larger than MAX_FILE_SIZE
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB

        cv_file = ("cv.pdf", BytesIO(large_content), "application/pdf")
        project_file = ("project.pdf", BytesIO(b"small"), "application/pdf")

        response = client.post(
            "/upload/",
            files={"cv": cv_file, "project_report": project_file},
        )

        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"].lower()

    def test_upload_creates_files_on_disk(
        self, client: TestClient, sample_cv_pdf_content: bytes, temp_upload_dir
    ):
        cv_file = ("cv.pdf", BytesIO(sample_cv_pdf_content), "application/pdf")
        project_file = (
            "project.pdf",
            BytesIO(sample_cv_pdf_content),
            "application/pdf",
        )

        response = client.post(
            "/upload/",
            files={"cv": cv_file, "project_report": project_file},
        )

        assert response.status_code == 200

        # Check CV file exists
        cv_dir = Path(temp_upload_dir) / "cv"
        assert cv_dir.exists()
        assert len(list(cv_dir.glob("*.pdf"))) == 1

        # Check project file exists
        project_dir = Path(temp_upload_dir) / "reports"
        assert project_dir.exists()
        assert len(list(project_dir.glob("*.pdf"))) == 1
