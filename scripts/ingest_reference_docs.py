import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag_service import RAGService
from app.config import settings


def main():
    print("Starting reference documents ingestion...\n")

    rag_service = RAGService()
    rag_service.initialize_collection()

    reference_dir = Path(settings.REFERENCE_DOCS_DIR)

    job_desc_dir = reference_dir / "job_descriptions"
    if job_desc_dir.exists() and job_desc_dir.is_dir():
        pdf_files = list(job_desc_dir.glob("*.pdf"))
        if pdf_files:
            print(f"Found {len(pdf_files)} job description(s)")
            for pdf_file in pdf_files:
                print(f"   Ingesting: {pdf_file.name}")
                rag_service.ingest_document(
                    document_path=str(pdf_file),
                    document_type="job_description",
                    document_id=f"job_desc_{pdf_file.stem}",
                )
        else:
            print("No job descriptions found in reference_docs/job_descriptions/")
    else:
        print("Job descriptions directory not found")

    case_study_file = reference_dir / "case_study_brief.pdf"
    if case_study_file.exists():
        print(f"\nIngesting case study brief: {case_study_file.name}")
        rag_service.ingest_document(
            document_path=str(case_study_file),
            document_type="case_study_brief",
            document_id="case_study_brief",
        )
    else:
        print("\nCase study brief not found: reference_docs/case_study_brief.pdf")

    rubrics_dir = reference_dir / "scoring_rubrics"
    if rubrics_dir.exists() and rubrics_dir.is_dir():
        pdf_files = list(rubrics_dir.glob("*.pdf"))
        if pdf_files:
            print(f"\nFound {len(pdf_files)} scoring rubric(s)")
            for pdf_file in pdf_files:
                print(f"   Ingesting: {pdf_file.name}")
                # Determine rubric type based on filename
                doc_type = (
                    "cv_scoring_rubric"
                    if "cv" in pdf_file.stem.lower()
                    else "project_scoring_rubric"
                )
                rag_service.ingest_document(
                    document_path=str(pdf_file),
                    document_type=doc_type,
                    document_id=f"rubric_{pdf_file.stem}",
                )
        else:
            print("\nNo scoring rubrics found in reference_docs/scoring_rubrics/")
    else:
        print("\nScoring rubrics directory not found")

    print("\nAll reference documents ingested successfully!")
    print(f"ChromaDB stored at: {settings.CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    main()
