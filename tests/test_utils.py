import os
from fastapi.datastructures import Headers
import httpx
import pytest
from pathlib import Path
from io import BytesIO
from fastapi import Header, UploadFile
import tempfile
import shutil

from tenacity import RetryError

from app.utils.file_handler import save_upload_file, delete_file
from app.utils.pdf_parser import extract_text_from_pdf, get_pdf_metadata
from app.core.exceptions import FileSizeException, FileTypeException
from app.config import settings
from app.utils.retry import retry_on_llm_error


class TestFileHandler:
    @pytest.fixture
    def temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_save_upload_file_success(
        self, sample_cv_pdf_content: bytes, temp_dir
    ):
        original_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = temp_dir

        # Create UploadFile
        upload_file = UploadFile(
            filename="test.pdf",
            file=BytesIO(sample_cv_pdf_content),
            headers=Headers({"content-type": "application/pdf"}),
        )

        filename, file_path, file_size = await save_upload_file(
            upload_file, "test_subdir"
        )

        assert filename.endswith(".pdf")
        assert Path(file_path).exists()
        assert file_size == len(sample_cv_pdf_content)

        settings.UPLOAD_DIR = original_dir

    @pytest.mark.asyncio
    async def test_save_upload_file_too_large(self, temp_dir):
        # Create file larger than MAX_FILE_SIZE
        large_content = b"x" * (settings.MAX_FILE_SIZE + 1)

        upload_file = UploadFile(
            filename="large.pdf",
            file=BytesIO(large_content),
            headers=Headers({"content-type": "application/pdf"}),
        )

        with pytest.raises(FileSizeException):
            await save_upload_file(upload_file, "test_subdir")

    @pytest.mark.asyncio
    async def test_save_upload_file_invalid_type(self, temp_dir):
        upload_file = UploadFile(
            filename="test.txt",
            file=BytesIO(b"text content"),
            headers=Headers({"content-type": "text/plain"}),
        )

        with pytest.raises(FileTypeException):
            await save_upload_file(upload_file, "test_subdir")

    @pytest.mark.asyncio
    async def test_save_upload_file_invalid_extension(
        self, sample_cv_pdf_content: bytes, temp_dir
    ):
        upload_file = UploadFile(
            filename="test.doc",
            file=BytesIO(sample_cv_pdf_content),
            headers=Headers({"content-type": "application/pdf"}),
        )

        with pytest.raises(FileTypeException):
            await save_upload_file(upload_file, "test_subdir")

    @pytest.mark.asyncio
    async def test_save_upload_file_creates_directory(
        self, sample_cv_pdf_content: bytes, temp_dir
    ):
        original_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = temp_dir

        upload_file = UploadFile(
            filename="test.pdf",
            file=BytesIO(sample_cv_pdf_content),
            headers=Headers({"content-type": "application/pdf"}),
        )

        subdir = "new/nested/dir"
        filename, file_path, file_size = await save_upload_file(upload_file, subdir)

        assert Path(temp_dir) / subdir in Path(file_path).parents
        assert Path(file_path).exists()

        settings.UPLOAD_DIR = original_dir

    def test_delete_file_success(self, temp_dir):
        # Create a test file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        assert test_file.exists()

        result = delete_file(str(test_file))

        assert result is True
        assert not test_file.exists()

    def test_delete_file_not_exists(self):
        result = delete_file("/nonexistent/file.txt")
        assert result is False

    def test_delete_file_permission_error(self, temp_dir):
        # This test might not work on all systems
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        try:
            os.chmod(test_file, 0o444)
            os.chmod(temp_dir, 0o444)

            result = delete_file(str(test_file))
            assert result is False
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_dir, 0o755)
            if test_file.exists():
                os.chmod(test_file, 0o644)


class TestPDFParser:
    def test_extract_text_from_pdf_success(
        self, sample_cv_pdf_content: bytes, tmp_path
    ):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(sample_cv_pdf_content)

        text = extract_text_from_pdf(str(pdf_file))

        assert text is not None
        assert isinstance(text, str)
        assert "Backend Developer" in text

    def test_extract_text_from_pdf_not_found(self):
        with pytest.raises(Exception):
            extract_text_from_pdf("/nonexistent/file.pdf")

    def test_extract_text_from_pdf_invalid(self, tmp_path):
        invalid_file = tmp_path / "invalid.pdf"
        invalid_file.write_text("This is not a PDF")

        with pytest.raises(Exception):
            extract_text_from_pdf(str(invalid_file))

    def test_get_pdf_metadata_success(self, sample_cv_pdf_content: bytes, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(sample_cv_pdf_content)

        metadata = get_pdf_metadata(str(pdf_file))

        assert metadata is not None
        assert "page_count" in metadata
        assert metadata["page_count"] >= 1

    def test_get_pdf_metadata_not_found(self):
        result = get_pdf_metadata("/nonexistent/file.pdf")
        assert result is None

    def test_get_pdf_metadata_invalid(self, tmp_path):
        invalid_file = tmp_path / "invalid.pdf"
        invalid_file.write_text("Not a PDF")

        result = get_pdf_metadata(str(invalid_file))
        assert result is None


class TestRetryDecorator:
    @pytest.mark.asyncio
    async def test_retry_on_llm_error_success(self):
        call_count = 0

        @retry_on_llm_error()
        async def mock_llm_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_llm_call()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_llm_error_with_retry(self):
        call_count = 0

        @retry_on_llm_error()
        async def mock_llm_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            return "success"

        result = await mock_llm_call()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_llm_error_max_retries(self):
        call_count = 0

        @retry_on_llm_error()
        async def mock_llm_call():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")

        with pytest.raises((httpx.TimeoutException, RetryError)):
            await mock_llm_call()

        # Should try 3 times (initial + 2 retries)
        assert call_count == 3
