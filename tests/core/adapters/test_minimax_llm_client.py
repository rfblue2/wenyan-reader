from pydantic import BaseModel

from wenyan.core.adapters.minimax_llm_client import MINIMAX_ANTHROPIC_BASE_URL, MiniMaxLLMClient


class _SampleModel(BaseModel):
    answer: str


def test_minimax_client_uses_anthropic_compatible_endpoint(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"content": [{"type": "text", "text": '{"answer": "ok"}'}]}

    def fake_post(self, url: str, **kwargs: object) -> FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse()

    monkeypatch.setattr("httpx.Client.post", fake_post)

    client = MiniMaxLLMClient("test-key", "MiniMax-M2.5-highspeed")
    result = client.complete_model(_FakePrompt(), _SampleModel)

    assert captured["url"] == f"{MINIMAX_ANTHROPIC_BASE_URL}/v1/messages"
    request_json = captured["json"]
    assert isinstance(request_json, dict)
    assert "system" in request_json
    assert "JSON object only" in str(request_json["system"])
    assert result.answer == "ok"


class _FakePrompt:
    template_name = "test"

    def render(self, _context: object) -> str:
        return "prompt"
