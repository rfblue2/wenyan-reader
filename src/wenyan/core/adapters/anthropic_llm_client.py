import time

import httpx
from pydantic import BaseModel

from wenyan.core.adapters.mock_llm_client import LLMParseError
from wenyan.core.adapters.structured_output import build_structured_system_prompt, parse_model_json
from wenyan.core.ports.llm_client import LLMClient, StructuredPrompt
from wenyan_models.config import RetryConfig

_TRANSIENT_EXCEPTIONS = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class AnthropicLLMClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://api.anthropic.com",
        retry: RetryConfig | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._messages_url = f"{base_url.rstrip('/')}/v1/messages"
        self._retry = retry or RetryConfig(max_attempts=3, backoff_seconds=2)
        self._timeout = httpx.Timeout(120.0, connect=30.0)

    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T:
        request_json = {
            "model": self._model,
            "max_tokens": 8192,
            "system": build_structured_system_prompt(model),
            "messages": [{"role": "user", "content": prompt.render({})}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(self._retry.max_attempts):
            if attempt > 0:
                time.sleep(self._retry.backoff_seconds * attempt)
            try:
                with httpx.Client(
                    timeout=self._timeout,
                    limits=httpx.Limits(max_keepalive_connections=0),
                ) as client:
                    response = client.post(
                        self._messages_url,
                        headers=headers,
                        json=request_json,
                    )
                response.raise_for_status()
                payload = response.json()
                text_blocks = [
                    block["text"]
                    for block in payload.get("content", [])
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if not text_blocks:
                    raise LLMParseError("anthropic response missing text content")
                return parse_model_json(text_blocks[0], model)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if (
                    exc.response.status_code in _RETRYABLE_STATUS_CODES
                    and attempt + 1 < self._retry.max_attempts
                ):
                    continue
                raise
            except (LLMParseError, *_TRANSIENT_EXCEPTIONS) as exc:
                last_error = exc
                if attempt + 1 < self._retry.max_attempts:
                    continue
                break
        raise LLMParseError(
            f"LLM request failed after {self._retry.max_attempts} attempts: {last_error}",
        ) from last_error
