from pathlib import Path

import pytest

from wenyan.core.adapters.prompt_template import load_prompt_template

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_ROOT = REPO_ROOT / "prompts"

_LLM_PROMPTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "paragraph-segmentation",
        "v1",
        ("paragraph_text", "paragraph_id", "input_hash"),
    ),
    (
        "paragraph-structure",
        "v1",
        ("chapter_text", "document_id", "chapter_id", "input_hash", "chapter_text_hash"),
    ),
    (
        "segment-tokenization",
        "v1",
        ("segment_text", "segment_id", "input_hash"),
    ),
    (
        "segment-tokenization-review",
        "v1",
        ("tokenization_json", "segment_id", "input_hash"),
    ),
)


@pytest.mark.parametrize(
    ("template_name", "version", "context_keys"),
    _LLM_PROMPTS,
    ids=[item[0] for item in _LLM_PROMPTS],
)
def test_llm_prompt_requests_structured_output(
    template_name: str,
    version: str,
    context_keys: tuple[str, ...],
) -> None:
    template = load_prompt_template(PROMPTS_ROOT, template_name, version)
    body = template.body

    assert "## Task" in body
    assert "## Output" in body
    assert "JSON object only" in body
    assert "schema from the system instructions" in body
    assert f"promptVersion: {template_name}-{version}" in body

    for key in context_keys:
        assert f"{{{{{key}}}}}" in body, f"missing placeholder for {key}"
