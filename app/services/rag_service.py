from typing import List
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.utils.pdf_parser import extract_text_from_pdf
from app.core.exceptions import RAGServiceException


class RAGService:
    def __init__(self):
        self.client = chromadb.Client(
            ChromaSettings(
                environment=settings.APP_ENV,
                is_persistent=True,
                persist_directory=settings.CHROMA_PERSIST_DIR,
                anonymized_telemetry=False,
            )
        )
        self.collection = None

    def initialize_collection(self, collection_name: str = "reference_docs"):
        """Initialize or get existing collection"""
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Reference documents for evaluation"},
            )
        except Exception as e:
            raise RAGServiceException(f"Failed to initialize collection: {str(e)}")

    def ingest_document(
        self,
        document_path: str,
        document_type: str,
        document_id: str,
    ):
        """Ingest a document into vector database"""
        try:
            text = extract_text_from_pdf(document_path)
            if not text:
                raise RAGServiceException("No text extracted from document")

            chunks = self._chunk_text(text, chunk_size=1000, overlap=100)

            if self.collection is None:
                raise RAGServiceException("Collection not initialized")

            for i, chunk in enumerate(chunks):
                self.collection.add(
                    documents=[chunk],
                    metadatas=[{"type": document_type, "chunk_index": i}],
                    ids=[f"{document_id}_chunk_{i}"],
                )
        except Exception as e:
            raise RAGServiceException(f"Failed to ingest document: {str(e)}")

    def retrieve_context(
        self,
        query: str,
        document_type: str,
        top_k: int = 3,
    ) -> str:
        """Retrieve relevant context from vector database"""
        try:
            if self.collection is None:
                raise RAGServiceException("Collection not initialized")

            results = self.collection.query(
                query_texts=[query], n_results=top_k, where={"type": document_type}
            )

            contexts = results["documents"][0] if results["documents"] else []
            return "\n\n".join(contexts)
        except Exception as e:
            raise RAGServiceException(f"Failed to retrieve context: {str(e)}")

    def _chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 100
    ) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap

        return chunks
