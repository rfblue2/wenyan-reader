
import httpx
from pydantic import BaseModel

from wenyan.core.adapters.mock_llm_client import LLMParseError
from wenyan.core.adapters.structured_output import build_structured_system_prompt, parse_model_json
from wenyan.core.ports.llm_client import LLMClient, StructuredPrompt


class AnthropicLLMClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://api.anthropic.com",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._messages_url = f"{base_url.rstrip('/')}/v1/messages"

    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T:
        response = httpx.post(
            self._messages_url,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": 4096,
                "system": build_structured_system_prompt(model),
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
        return parse_model_json(text_blocks[0], model)
