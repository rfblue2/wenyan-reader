import pytest
from pydantic import BaseModel

from wenyan.core.adapters.mock_llm_client import LLMParseError
from wenyan.core.adapters.structured_output import (
    build_structured_system_prompt,
    extract_json_text,
    parse_model_json,
)
from wenyan_models.artifacts.paragraph import ParagraphDraft


class _SampleModel(BaseModel):
    answer: str


def test_build_structured_system_prompt_includes_schema() -> None:
    prompt = build_structured_system_prompt(_SampleModel)
    assert "JSON object only" in prompt
    assert '"answer"' in prompt


def test_extract_json_text_from_fence() -> None:
    raw = 'Here is the result:\n```json\n{"answer": "ok"}\n```'
    assert extract_json_text(raw) == '{"answer": "ok"}'


def test_extract_json_text_from_embedded_object() -> None:
    raw = 'Sure! {"answer": "ok"} thanks'
    assert extract_json_text(raw) == '{"answer": "ok"}'


def test_parse_model_json_validates_payload() -> None:
    result = parse_model_json('{"answer": "ok"}', _SampleModel)
    assert result.answer == "ok"


def test_parse_model_json_raises_on_invalid_payload() -> None:
    with pytest.raises(LLMParseError):
        parse_model_json("not json", _SampleModel)


def test_build_structured_system_prompt_uses_serialization_aliases() -> None:
    prompt = build_structured_system_prompt(ParagraphDraft)
    assert "paragraphId" in prompt
    assert "paragraph_id" not in prompt
