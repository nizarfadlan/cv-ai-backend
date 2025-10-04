import ast
import re
from typing import Dict, Optional
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

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        text = text.strip()

        # Method 1: Find JSON code block
        json_block_pattern = r"```json\s*(\{.*?\})\s*```"
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1)

        # Method 2: Find any code block
        code_block_pattern = r"```\s*(\{.*?\})\s*```"
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1)

        # Method 3: Extract JSON object (handles nested objects)
        json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            return max(matches, key=len)

        return None

    def _parse_json_response(self, response: str) -> Dict:
        # Clean response
        response = response.strip()

        # Try direct parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(response)
            except Exception:
                pass

        # Try extracting JSON from text
        extracted_json = self._extract_json_from_text(response)
        if extracted_json:
            try:
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                # Try with ast.literal_eval
                try:
                    return ast.literal_eval(extracted_json)
                except Exception:
                    pass

        # Last resort: manual extraction
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Find first { and last }
        first_brace = response.find("{")
        last_brace = response.rfind("}")
        if first_brace != -1 and last_brace != -1:
            response = response[first_brace : last_brace + 1]
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(response)
                except Exception:
                    pass

        raise LLMServiceException(
            f"Failed to extract valid JSON from response. First 500 chars: {response[:500]}"
        )

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

CRITICAL INSTRUCTION: Your response must be ONLY a valid JSON object. Do not add any text before or after the JSON. Start your response with {{ and end with }}.

Required JSON format:
{{
    "technical_skills_score": <1-5>,
    "experience_level_score": <1-5>,
    "achievements_score": <1-5>,
    "cultural_fit_score": <1-5>,
    "cv_match_rate": <0.0-1.0>,
    "feedback": "<detailed feedback in 2-3 sentences>"
}}

Respond with JSON only:"""

        response = await self.generate_completion(prompt, temperature=0.2)

        try:
            result = self._parse_json_response(response)
            required_fields = [
                "technical_skills_score",
                "experience_level_score",
                "achievements_score",
                "cultural_fit_score",
                "cv_match_rate",
                "feedback",
            ]
            for field in required_fields:
                if field not in result:
                    raise LLMServiceException(f"Missing required field: {field}")
            return result
        except Exception as e:
            raise LLMServiceException(f"Failed to parse CV evaluation: {str(e)}")

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

CRITICAL INSTRUCTION: Your response must be ONLY a valid JSON object. Do not add any text before or after the JSON. Start your response with {{ and end with }}.

Required JSON format:
{{
    "correctness_score": <1-5>,
    "code_quality_score": <1-5>,
    "resilience_score": <1-5>,
    "documentation_score": <1-5>,
    "creativity_score": <1-5>,
    "project_score": <1.0-5.0>,
    "feedback": "<detailed feedback in 2-3 sentences>"
}}

Respond with JSON only:"""

        response = await self.generate_completion(prompt, temperature=0.2)

        try:
            result = self._parse_json_response(response)
            required_fields = [
                "correctness_score",
                "code_quality_score",
                "resilience_score",
                "documentation_score",
                "creativity_score",
                "project_score",
                "feedback",
            ]
            for field in required_fields:
                if field not in result:
                    raise LLMServiceException(f"Missing required field: {field}")
            return result
        except Exception as e:
            print(f"[Project Evaluation] Failed to parse response: {response[:500]}")
            raise LLMServiceException(f"Failed to parse project evaluation: {str(e)}")

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
