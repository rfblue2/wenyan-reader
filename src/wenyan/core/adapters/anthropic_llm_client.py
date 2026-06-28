
import httpx
from pydantic import BaseModel, TypeAdapter

from wenyan.core.adapters.mock_llm_client import LLMParseError
from wenyan.core.ports.llm_client import StructuredPrompt


class AnthropicLLMClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt.render({})}],
            },
            timeout=120.0,
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
        try:
            parsed = TypeAdapter(model).validate_json(text_blocks[0])
        except Exception as exc:  # noqa: BLE001
            raise LLMParseError(str(exc)) from exc
        return parsed
