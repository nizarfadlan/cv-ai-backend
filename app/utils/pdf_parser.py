from traceback import print_exc
from typing import Optional, TypedDict
import pypdf


class PDFMetadata(TypedDict):
    page_count: int
    author: str
    title: str
    subject: str


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extract text content from PDF file"""
    try:
        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        print_exc()
        raise Exception(f"Failed to parse PDF: {str(e)}")


def get_pdf_metadata(file_path: str) -> Optional[PDFMetadata]:
    """Extract metadata from PDF file"""
    try:
        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            metadata = pdf_reader.metadata
            if metadata is None:
                return None

            return PDFMetadata(
                page_count=len(pdf_reader.pages),
                author=metadata.get("/Author", ""),
                title=metadata.get("/Title", ""),
                subject=metadata.get("/Subject", ""),
            )
    except Exception:
        print_exc()
        return None
