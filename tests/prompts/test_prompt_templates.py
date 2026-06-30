from pathlib import Path

import pytest

from wenyan.core.adapters.prompt_template import load_prompt_template

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_ROOT = REPO_ROOT / "prompts"

_LLM_PROMPTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "paragraph-segmentation",
        ("paragraph_text", "paragraph_id", "input_hash"),
    ),
    (
        "paragraph-structure",
        ("chapter_text", "document_id", "chapter_id", "input_hash", "chapter_text_hash"),
    ),
    (
        "segment-tokenization",
        ("segment_text", "segment_id", "input_hash"),
    ),
    (
        "segment-tokenization-review",
        ("tokenization_json", "segment_id", "review_input_hash"),
    ),
    (
        "segment-gloss",
        (
            "segment_text",
            "segment_id",
            "input_hash",
            "tokenization_json",
            "candidate_glosses_json",
        ),
    ),
    (
        "segment-gloss-review",
        ("glosses_json", "segment_id", "review_input_hash", "segment_text", "tokenization_json", "candidate_glosses_json"),
    ),
    (
        "segment-grammar",
        ("segment_text", "segment_id", "input_hash", "tokenization_json", "local_context_json"),
    ),
    (
        "segment-grammar-review",
        (
            "grammar_notes_json",
            "segment_id",
            "review_input_hash",
            "segment_text",
            "tokenization_json",
            "glosses_json",
            "local_context_json",
        ),
    ),
    (
        "review-paragraph-assembly",
        (
            "paragraph_id",
            "review_input_hash",
            "paragraph_package_json",
            "paragraph_draft_json",
        ),
    ),
)


@pytest.mark.parametrize(
    ("template_name", "context_keys"),
    _LLM_PROMPTS,
    ids=[item[0] for item in _LLM_PROMPTS],
)
def test_llm_prompt_requests_structured_output(
    template_name: str,
    context_keys: tuple[str, ...],
) -> None:
    template = load_prompt_template(PROMPTS_ROOT, template_name)
    body = template.body

    assert "## Task" in body
    assert "## Output" in body
    assert "JSON object only" in body
    assert "schema from the system instructions" in body
    assert "promptVersion" not in body

    for key in context_keys:
        assert f"{{{{{key}}}}}" in body, f"missing placeholder for {key}"
