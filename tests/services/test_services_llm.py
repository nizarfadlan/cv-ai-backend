import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.services.llm_service import LLMService
from app.core.exceptions import LLMServiceException


class TestLLMService:
    @pytest.fixture
    def llm_service(self):
        return LLMService()

    def test_extract_json_from_text_with_code_block(self, llm_service):
        text = """```json
{
    "score": 4,
    "feedback": "Good work"
}
```"""

        result = llm_service._extract_json_from_text(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["score"] == 4

    def test_extract_json_from_plain_text(self, llm_service):
        text = """Here is the result:
{"score": 5, "feedback": "Excellent"}
That's all."""

        result = llm_service._extract_json_from_text(text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["score"] == 5

    def test_parse_json_response_valid(self, llm_service):
        response = '{"score": 4, "feedback": "Good"}'

        result = llm_service._parse_json_response(response)
        assert result["score"] == 4
        assert result["feedback"] == "Good"

    def test_parse_json_response_with_markdown(self, llm_service):
        response = """```json
{
    "score": 3,
    "feedback": "Average"
}
```"""

        result = llm_service._parse_json_response(response)
        assert result["score"] == 3

    def test_parse_json_response_invalid(self, llm_service):
        response = "This is not JSON at all"

        with pytest.raises(LLMServiceException):
            llm_service._parse_json_response(response)

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, llm_service):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"result": "success"}'}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await llm_service.generate_completion("Test prompt")

            assert '{"result": "success"}' in result
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_completion_api_error(self, llm_service):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_response
            )

            with pytest.raises(LLMServiceException):
                await llm_service.generate_completion("Test prompt")

    @pytest.mark.asyncio
    async def test_evaluate_cv_success(self, llm_service):
        mock_response = """{
            "technical_skills_score": 4,
            "experience_level_score": 3,
            "achievements_score": 4,
            "cultural_fit_score": 5,
            "cv_match_rate": 0.82,
            "feedback": "Strong candidate"
        }"""

        with patch.object(
            llm_service, "generate_completion", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await llm_service.evaluate_cv(
                cv_text="Sample CV text",
                job_description="Job requirements",
                scoring_rubric="Scoring criteria",
            )

            assert result["technical_skills_score"] == 4
            assert result["cv_match_rate"] == 0.82
            assert "feedback" in result

    @pytest.mark.asyncio
    async def test_evaluate_cv_missing_fields(self, llm_service):
        mock_response = '{"technical_skills_score": 4}'

        with patch.object(
            llm_service, "generate_completion", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            with pytest.raises(LLMServiceException):
                await llm_service.evaluate_cv(
                    cv_text="Sample CV",
                    job_description="Job desc",
                    scoring_rubric="Rubric",
                )

    @pytest.mark.asyncio
    async def test_evaluate_project_success(self, llm_service):
        mock_response = """{
            "correctness_score": 4,
            "code_quality_score": 5,
            "resilience_score": 4,
            "documentation_score": 5,
            "creativity_score": 3,
            "project_score": 4.5,
            "feedback": "Well-implemented"
        }"""

        with patch.object(
            llm_service, "generate_completion", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await llm_service.evaluate_project(
                project_text="Project report",
                case_study_brief="Case study",
                scoring_rubric="Scoring criteria",
            )

            assert result["project_score"] == 4.5
            assert result["code_quality_score"] == 5

    @pytest.mark.asyncio
    async def test_synthesize_summary_success(self, llm_service):
        cv_eval = {"cv_match_rate": 0.82, "feedback": "Strong skills"}
        project_eval = {"project_score": 4.5, "feedback": "Good implementation"}

        mock_response = (
            "Overall, this is a recommended candidate with strong technical background."
        )

        with patch.object(
            llm_service, "generate_completion", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await llm_service.synthesize_summary(
                cv_evaluation=cv_eval,
                project_evaluation=project_eval,
                job_title="Backend Developer",
            )

            assert "recommended" in result.lower()
            assert len(result) > 0
