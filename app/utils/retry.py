from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx


def retry_on_llm_error():
    """Decorator for retrying LLM API calls with exponential backoff"""
    return retry(
        retry=retry_if_exception_type(
            (
                httpx.HTTPStatusError,
                httpx.TimeoutException,
                httpx.ConnectError,
            )
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
