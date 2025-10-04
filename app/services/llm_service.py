from typing import Dict
import httpx
import json
from app.config import settings
from app.utils.retry import retry_on_llm_error
from app.core.exceptions import LLMServiceException


class LLMService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    @retry_on_llm_error()
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Generate LLM completion"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise LLMServiceException(
                f"OpenRouter API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise LLMServiceException(f"LLM generation failed: {str(e)}")

    async def evaluate_cv(
        self,
        cv_text: str,
        job_description: str,
        scoring_rubric: str,
    ) -> Dict:
        """Evaluate CV against job description"""
        prompt = f"""You are an expert HR evaluator. Analyze the candidate's CV against the job description and scoring rubric.

JOB DESCRIPTION:
{job_description}

SCORING RUBRIC:
{scoring_rubric}

CANDIDATE CV:
{cv_text}

Provide evaluation in JSON format only (no markdown, no extra text):
{{
    "technical_skills_score": <1-5>,
    "experience_level_score": <1-5>,
    "achievements_score": <1-5>,
    "cultural_fit_score": <1-5>,
    "cv_match_rate": <0.0-1.0>,
    "feedback": "<detailed feedback in 2-3 sentences>"
}}"""

        response = await self.generate_completion(prompt, temperature=0.2)

        # Clean response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise LLMServiceException(f"Failed to parse LLM response as JSON: {str(e)}")

    async def evaluate_project(
        self,
        project_text: str,
        case_study_brief: str,
        scoring_rubric: str,
    ) -> Dict:
        """Evaluate project report against case study brief"""
        prompt = f"""You are an expert technical evaluator. Analyze the project report against the case study brief and scoring rubric.

CASE STUDY BRIEF:
{case_study_brief}

SCORING RUBRIC:
{scoring_rubric}

PROJECT REPORT:
{project_text}

Provide evaluation in JSON format only (no markdown, no extra text):
{{
    "correctness_score": <1-5>,
    "code_quality_score": <1-5>,
    "resilience_score": <1-5>,
    "documentation_score": <1-5>,
    "creativity_score": <1-5>,
    "project_score": <1.0-5.0>,
    "feedback": "<detailed feedback in 2-3 sentences>"
}}"""

        response = await self.generate_completion(prompt, temperature=0.2)

        # Clean response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise LLMServiceException(f"Failed to parse LLM response as JSON: {str(e)}")

    async def synthesize_summary(
        self,
        cv_evaluation: Dict,
        project_evaluation: Dict,
        job_title: str,
    ) -> str:
        """Generate overall summary from both evaluations"""
        prompt = f"""Synthesize an overall evaluation summary for a {job_title} candidate.

CV EVALUATION:
- Match Rate: {cv_evaluation.get("cv_match_rate")}
- Feedback: {cv_evaluation.get("feedback")}

PROJECT EVALUATION:
- Score: {project_evaluation.get("project_score")}
- Feedback: {project_evaluation.get("feedback")}

Provide 3-5 sentences covering:
1. Key strengths
2. Notable gaps or areas for improvement
3. Hiring recommendation (recommended/conditional/not recommended)

Keep it professional and concise."""

        return await self.generate_completion(prompt, temperature=0.2, max_tokens=500)
