import pytest
from unittest.mock import patch

from app.services.rag_service import RAGService
from app.core.exceptions import RAGServiceException


class TestRAGService:
    @pytest.fixture
    def rag_service(self, temp_chroma_dir):
        return RAGService()

    @pytest.fixture
    def sample_pdf_file(self, tmp_path, sample_cv_pdf_content):
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(sample_cv_pdf_content)
        return str(pdf_file)

    def test_initialize_collection_success(self, rag_service):
        rag_service.initialize_collection("test_collection")

        assert rag_service.collection is not None
        assert rag_service.collection.name == "test_collection"

    def test_initialize_collection_twice(self, rag_service):
        rag_service.initialize_collection("test_collection")
        first_collection = rag_service.collection

        rag_service.initialize_collection("test_collection")
        second_collection = rag_service.collection

        assert first_collection.name == second_collection.name

    def test_chunk_text_basic(self, rag_service):
        text = "a" * 2500
        chunks = rag_service._chunk_text(text, chunk_size=1000, overlap=100)

        assert len(chunks) > 1
        assert len(chunks[0]) == 1000

        # Check overlap
        assert chunks[0][-100:] == chunks[1][:100]

    def test_chunk_text_small_text(self, rag_service):
        text = "Short text"
        chunks = rag_service._chunk_text(text, chunk_size=1000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_custom_parameters(self, rag_service):
        text = "x" * 3000
        chunks = rag_service._chunk_text(text, chunk_size=500, overlap=50)

        assert len(chunks) > 0
        assert len(chunks[0]) == 500

    @patch("app.services.rag_service.extract_text_from_pdf")
    def test_ingest_document_success(self, mock_extract, rag_service, sample_pdf_file):
        mock_extract.return_value = "Sample document text for testing"

        rag_service.initialize_collection()
        rag_service.ingest_document(
            document_path=sample_pdf_file,
            document_type="job_description",
            document_id="test_doc_1",
        )

        mock_extract.assert_called_once_with(sample_pdf_file)

        # Verify document was added to collection
        result = rag_service.collection.get(ids=["test_doc_1_chunk_0"])
        assert len(result["ids"]) > 0

    @patch("app.services.rag_service.extract_text_from_pdf")
    def test_ingest_document_no_text(self, mock_extract, rag_service, sample_pdf_file):
        mock_extract.return_value = ""

        rag_service.initialize_collection()

        with pytest.raises(
            RAGServiceException, match="No text extracted from document"
        ):
            rag_service.ingest_document(
                document_path=sample_pdf_file,
                document_type="job_description",
                document_id="test_doc_2",
            )

    def test_ingest_document_without_collection(self, rag_service, sample_pdf_file):
        with pytest.raises(RAGServiceException, match="Collection not initialized"):
            rag_service.ingest_document(
                document_path=sample_pdf_file,
                document_type="job_description",
                document_id="test_doc_3",
            )

    @patch("app.services.rag_service.extract_text_from_pdf")
    def test_retrieve_context_success(self, mock_extract, rag_service, sample_pdf_file):
        mock_extract.return_value = (
            "Backend developer job requirements include Python and FastAPI experience"
        )

        rag_service.initialize_collection()
        rag_service.ingest_document(
            document_path=sample_pdf_file,
            document_type="job_description",
            document_id="test_doc_4",
        )

        context = rag_service.retrieve_context(
            query="Python backend developer", document_type="job_description", top_k=2
        )

        assert isinstance(context, str)
        assert len(context) > 0

    def test_retrieve_context_without_collection(self, rag_service):
        with pytest.raises(RAGServiceException):
            rag_service.retrieve_context(
                query="test query", document_type="job_description", top_k=3
            )

    @patch("app.services.rag_service.extract_text_from_pdf")
    def test_retrieve_context_no_results(
        self, mock_extract, rag_service, sample_pdf_file
    ):
        mock_extract.return_value = "Some unrelated text about cooking recipes"

        rag_service.initialize_collection()
        rag_service.ingest_document(
            document_path=sample_pdf_file,
            document_type="cv_scoring_rubric",
            document_id="test_doc_5",
        )

        # Query for different document type
        context = rag_service.retrieve_context(
            query="programming", document_type="job_description", top_k=3
        )

        # Should return empty string when no matches
        assert context == ""

    @patch("app.services.rag_service.extract_text_from_pdf")
    def test_ingest_multiple_documents(
        self, mock_extract, rag_service, sample_pdf_file
    ):
        rag_service.initialize_collection()

        # Ingest first document
        mock_extract.return_value = "First document text"
        rag_service.ingest_document(
            document_path=sample_pdf_file,
            document_type="job_description",
            document_id="doc_1",
        )

        # Ingest second document
        mock_extract.return_value = "Second document text"
        rag_service.ingest_document(
            document_path=sample_pdf_file,
            document_type="job_description",
            document_id="doc_2",
        )

        # Verify both documents exist
        result = rag_service.collection.get()
        assert len(result["ids"]) >= 2
