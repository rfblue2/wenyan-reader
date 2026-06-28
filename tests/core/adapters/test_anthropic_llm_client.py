import httpx
from pydantic import BaseModel

from wenyan.core.adapters.anthropic_llm_client import AnthropicLLMClient
from wenyan.core.adapters.mock_llm_client import LLMParseError
from wenyan_models.config import RetryConfig


class _SampleModel(BaseModel):
    answer: str


class _FakePrompt:
    template_name = "test"

    def render(self, _context: object) -> str:
        return "prompt"


def test_retries_transient_remote_protocol_error(monkeypatch) -> None:
    calls = {"count": 0}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"content": [{"type": "text", "text": '{"answer": "ok"}'}]}

    def fake_post(self, *_args: object, **_kwargs: object) -> FakeResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return FakeResponse()

    monkeypatch.setattr("httpx.Client.post", fake_post)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    client = AnthropicLLMClient(
        "test-key",
        "test-model",
        retry=RetryConfig(max_attempts=3, backoff_seconds=2),
    )
    result = client.complete_model(_FakePrompt(), _SampleModel)

    assert result.answer == "ok"
    assert calls["count"] == 2


def test_does_not_retry_parse_errors(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"content": [{"type": "text", "text": "not json"}]}

    monkeypatch.setattr("httpx.Client.post", lambda *_a, **_k: FakeResponse())

    client = AnthropicLLMClient(
        "test-key",
        "test-model",
        retry=RetryConfig(max_attempts=3, backoff_seconds=2),
    )
    try:
        client.complete_model(_FakePrompt(), _SampleModel)
    except LLMParseError:
        return
    raise AssertionError("expected LLMParseError")
