import json
import re

from pydantic import BaseModel, TypeAdapter

from wenyan.core.adapters.mock_llm_client import LLMParseError


def build_structured_system_prompt(model: type[BaseModel]) -> str:
    schema = model.model_json_schema(mode="serialization")
    schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
    return f"""You are a preprocessing assistant for Classical Chinese texts.

Respond with a single JSON object only. No markdown fences, no commentary, and no prose before or after the JSON.

The JSON must validate against this schema:
{schema_json}

Rules:
- Use camelCase property names exactly as in the schema.
- Echo identifier and hash fields from the user message (PARAGRAPH_ID, INPUT_HASH, SEGMENT_ID, DOCUMENT_ID, CHAPTER_ID, and similar labels) into the matching JSON properties.
- Set promptVersion to the value from the task section in the user message.
- Set model to "pending" and attempts to 1 unless the user message specifies otherwise.
- Generate new UUID v4 strings for id fields you must create.
- Text spans must be exact substrings of the source text; do not normalize or rewrite characters.
- For review artifacts, status must be exactly "approved" or "rejected" as defined in the schema.
- Omit optional properties when empty rather than inventing placeholder content.
"""


def extract_json_text(raw: str) -> str:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_model_json[T: BaseModel](raw: str, model: type[T]) -> T:
    try:
        return TypeAdapter(model).validate_json(extract_json_text(raw))
    except Exception as exc:  # noqa: BLE001
        raise LLMParseError(str(exc)) from exc
