import asyncio
from typing import Dict
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.utils.pdf_parser import extract_text_from_pdf
from app.repositories.document import DocumentRepository
from app.repositories.evaluation import EvaluationRepository
from app.models.evaluation import EvaluationStatus


class EvaluationService:
    def __init__(self):
        self.llm_service = LLMService()
        self.rag_service = RAGService()
        self.rag_service.initialize_collection()

    async def process_evaluation(
        self,
        evaluation_id: str,
        doc_repo: DocumentRepository,
        eval_repo: EvaluationRepository,
    ) -> Dict:
        """Main evaluation pipeline"""

        # Get evaluation record
        evaluation = eval_repo.get(evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found")

        # Update status to processing
        eval_repo.update_status(evaluation, EvaluationStatus.PROCESSING)

        try:
            # Get documents
            cv_doc = doc_repo.get(str(evaluation.cv_document_id))
            project_doc = doc_repo.get(str(evaluation.project_document_id))

            # Extract text from documents
            cv_text = extract_text_from_pdf(cv_doc.file_path)
            project_text = extract_text_from_pdf(project_doc.file_path)

            if not cv_text or not project_text:
                raise ValueError("Failed to extract text from one or both documents")

            # Retrieve relevant context from RAG
            job_desc_context = self.rag_service.retrieve_context(
                query=cv_text[:500],  # Use CV snippet as query
                document_type="job_description",
                top_k=3,
            )

            cv_rubric_context = self.rag_service.retrieve_context(
                query="CV evaluation criteria scoring rubric",
                document_type="cv_scoring_rubric",
                top_k=2,
            )

            case_study_context = self.rag_service.retrieve_context(
                query=project_text[:500], document_type="case_study_brief", top_k=3
            )

            project_rubric_context = self.rag_service.retrieve_context(
                query="Project evaluation criteria scoring rubric",
                document_type="project_scoring_rubric",
                top_k=2,
            )

            # Stage 1: Evaluate CV and Project
            cv_evaluation, project_evaluation = await asyncio.gather(
                self.llm_service.evaluate_cv(
                    cv_text=cv_text,
                    job_description=job_desc_context,
                    scoring_rubric=cv_rubric_context,
                ),
                self.llm_service.evaluate_project(
                    project_text=project_text,
                    case_study_brief=case_study_context,
                    scoring_rubric=project_rubric_context,
                ),
            )

            # Stage 3: Synthesize overall summary
            overall_summary = await self.llm_service.synthesize_summary(
                cv_evaluation=cv_evaluation,
                project_evaluation=project_evaluation,
                job_title=evaluation.job_title,
            )

            # Prepare results
            results = {
                "cv_match_rate": cv_evaluation.get("cv_match_rate"),
                "cv_feedback": cv_evaluation.get("feedback"),
                "project_score": project_evaluation.get("project_score"),
                "project_feedback": project_evaluation.get("feedback"),
                "overall_summary": overall_summary,
                "cv_detailed_scores": {
                    "technical_skills": cv_evaluation.get("technical_skills_score"),
                    "experience_level": cv_evaluation.get("experience_level_score"),
                    "achievements": cv_evaluation.get("achievements_score"),
                    "cultural_fit": cv_evaluation.get("cultural_fit_score"),
                },
                "project_detailed_scores": {
                    "correctness": project_evaluation.get("correctness_score"),
                    "code_quality": project_evaluation.get("code_quality_score"),
                    "resilience": project_evaluation.get("resilience_score"),
                    "documentation": project_evaluation.get("documentation_score"),
                    "creativity": project_evaluation.get("creativity_score"),
                },
            }

            # Save results
            eval_repo.save_results(evaluation, results)

            return results

        except Exception as e:
            # Update status to failed
            eval_repo.update_failed_status(evaluation, str(e))
            raise
