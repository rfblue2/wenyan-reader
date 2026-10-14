# LLM Output Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise LLM call success rate by making invalid output unrepresentable (response schemas separate from artifact schemas), enforcing schemas at the API via forced tool use, and adding bounded semantic feedback retries — starting with the gloss job pilot that closes the [code-audit gloss linking bug](../code-audit.md).

**Architecture:** Each LLM job gets a slim **wire model** (what the model decides) and a deterministic **wire → artifact** assembler (UUID minting, metadata stamping, dedupe). `AnthropicLLMClient` and `MiniMaxLLMClient` share one forced-tool code path. Semantic invariants that JSON Schema cannot express are checked in Python; failures refeed into the same conversation (max 3 attempts). Promote-time validation stays the final gate but should rarely fire.

**Tech Stack:** Python 3.12+, Pydantic v2, httpx, Anthropic Messages API (`tools` + `tool_choice` + optional `strict: true`), existing `MockLLMClient` / `build_job_context` test fixtures.

**Spec:** [llm-correctness.md](../llm-correctness.md)

---

## File map

| File | Responsibility |
| --- | --- |
| `packages/wenyan-models/src/wenyan_models/llm/gloss.py` | `GlossResponse`, per-decision wire types |
| `packages/wenyan-models/src/wenyan_models/llm/__init__.py` | Re-exports for wire models |
| `src/wenyan/core/gloss/assemble_glosses.py` | `assemble_glosses_artifact(response, tokenization, candidates) -> GlossesArtifact` |
| `src/wenyan/core/gloss/validate_gloss_response.py` | Semantic validators (coverage, pinyin) |
| `src/wenyan/core/adapters/api_json_schema.py` | Pydantic → API-safe JSON Schema (`additionalProperties: false`, full `required`) |
| `src/wenyan/core/adapters/forced_tool_output.py` | Build tool defs, parse `tool_use` blocks |
| `src/wenyan/core/adapters/structured_output.py` | Slim system prompt; keep `extract_json_text` for legacy/mock fallback only |
| `src/wenyan/core/adapters/anthropic_llm_client.py` | Forced tool use + feedback conversation loop |
| `src/wenyan/core/ports/llm_client.py` | Optional `SemanticValidator` protocol; `LLMSemanticValidationError` |
| `src/wenyan/jobs/segment_runner.py` | `SegmentAnnotateJobSpec` gains `response_model` + `wire_to_artifact` |
| `src/wenyan/core/gloss/filter_candidates.py` | `filter_candidates_by_token_surfaces` — prompt-only subset |
| `src/wenyan/jobs/gloss_segment.py` | Pilot: call wire model, assemble artifact; filtered prompt candidates |
| `src/wenyan/jobs/review_segment_gloss.py` | Same surface filter for gloss review prompt |
| `prompts/segment-gloss.md` | Drop echo fields and UUID instructions |
| `src/wenyan/core/adapters/mock_llm_client.py` | `_glosses` returns `GlossResponse` shape |
| `tests/core/gloss/test_assemble_glosses.py` | Unit tests for wire → artifact |
| `tests/core/adapters/test_api_json_schema.py` | Schema hardening |
| `tests/core/adapters/test_anthropic_llm_client.py` | Tool-use request/response + feedback retry |
| `tests/jobs/test_gloss_segment.py` | Integration unchanged at artifact boundary |

**Out of scope (separate backlog):** merging review passes (architecture-audit §1.1), deterministic tokenization offset/coverage (§2.2), post-hoc gloss id normalizer (explicitly rejected by spec).

---

## Phase 0 — Candidate gloss prompt filtering (cost + schema size)

Ship first or alongside Phase 1 Task 1. Independent of wire-schema work; closes [architecture-audit §3.2](../architecture-audit.md).

**Rule:** Include a glossary entry in the LLM prompt **only when `entry.surface` equals some `token.surface` in the segment tokenization.** No substring or character-component matching — exact token surface only.

**Why this is safe:**
- Reuse decisions are always per-token; an entry for `國` cannot apply if no token has surface `國`.
- Polyphonic characters (`將` → `jiàng` vs `jiāng`) need **all** prior senses for that surface in the prompt so the model can pick or reuse the right one — surface filter keeps every relevant sense, drops everything else.
- `normalize_gloss_reuse` and assembly still use the **full** `load_candidate_glosses()` result so deterministic dedupe by `(surface, pinyin, gloss)` is unchanged.

**Prompt vs post-process split:**

| Stage | Candidate set |
| --- | --- |
| `candidate_glosses_json` in gloss + gloss-review prompts | Filtered by token surfaces |
| `normalize_gloss_reuse`, `assemble_glosses_artifact`, semantic `reuseGlossId` validation | Full glossary |

### Task 0: Surface-filtered prompt candidates

**Files:**
- Create: `src/wenyan/core/gloss/filter_candidates.py`
- Modify: `src/wenyan/jobs/gloss_segment.py` (`_prepare_gloss`)
- Modify: `src/wenyan/jobs/review_segment_gloss.py` (`_prepare_gloss_review`)
- Modify: `prompts/segment-gloss.md` — note list is “candidates for token surfaces in this segment”
- Test: `tests/core/gloss/test_filter_candidates.py`

- [x] **Step 1: Write failing tests**

```python
# tests/core/gloss/test_filter_candidates.py
from wenyan.core.gloss.filter_candidates import filter_candidates_by_token_surfaces
from wenyan_models.artifacts.segment import GlossEntry, TokenizationArtifact


def test_keeps_entries_whose_surface_appears_on_a_token() -> None:
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "mock",
            "inputHash": "sha256:x",
            "attempts": 1,
            "text": "將聽",
            "tokens": [
                {"id": "t1", "surface": "將", "start": 0, "end": 1},
                {"id": "t2", "surface": "聽", "start": 1, "end": 2},
            ],
        },
    )
    candidates = (
        GlossEntry(id="g-jiang", surface="將", pinyin="jiāng", gloss="will"),
        GlossEntry(id="g-guo", surface="國", pinyin="guó", gloss="state"),
        GlossEntry(id="g-ting", surface="聽", pinyin="tīng", gloss="hear"),
    )
    filtered = filter_candidates_by_token_surfaces(candidates, tokenization)
    assert {e.id for e in filtered} == {"g-jiang", "g-ting"}


def test_returns_empty_when_no_surface_overlap() -> None:
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "mock",
            "inputHash": "sha256:x",
            "attempts": 1,
            "text": "兵",
            "tokens": [{"id": "t1", "surface": "兵", "start": 0, "end": 1}],
        },
    )
    candidates = (GlossEntry(id="g-guo", surface="國", pinyin="guó", gloss="state"),)
    assert filter_candidates_by_token_surfaces(candidates, tokenization) == ()
```

- [x] **Step 2: Implement filter**

```python
# src/wenyan/core/gloss/filter_candidates.py
from wenyan_models.artifacts.segment import GlossEntry, TokenizationArtifact


def filter_candidates_by_token_surfaces(
    candidates: tuple[GlossEntry, ...],
    tokenization: TokenizationArtifact,
) -> tuple[GlossEntry, ...]:
    surfaces = {token.surface for token in tokenization.tokens}
    return tuple(entry for entry in candidates if entry.surface in surfaces)
```

- [x] **Step 3: Use in `_prepare_gloss` and `_prepare_gloss_review`**

```python
all_candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
prompt_candidates = filter_candidates_by_token_surfaces(all_candidates, tokenization)
# candidate_glosses_json ← prompt_candidates only
```

Leave `_post_process_gloss` / `normalize_gloss_reuse` on `all_candidates`.

- [x] **Step 4: Run tests — commit**

```bash
uv run python -m pytest tests/core/gloss/test_filter_candidates.py tests/jobs/test_gloss_segment.py -q
```

---

## Phase 1 — Gloss response schema pilot (Layer 1)

Closes the High-priority gloss decision ↔ entry linking bug without a normalizer.

### Task 1: Wire models for gloss

**Files:**
- Create: `packages/wenyan-models/src/wenyan_models/llm/__init__.py`
- Create: `packages/wenyan-models/src/wenyan_models/llm/gloss.py`
- Test: `tests/models/test_gloss_response_models.py`

- [ ] **Step 1: Write failing model tests**

```python
# tests/models/test_gloss_response_models.py
import pytest
from pydantic import ValidationError
from wenyan_models.llm.gloss import CreateGlossDecision, GlossResponse, ReuseGlossDecision


def test_reuse_decision_parses() -> None:
    item = ReuseGlossDecision.model_validate(
        {"tokenId": "t-1", "reuseGlossId": "g-existing"},
    )
    assert item.token_id == "t-1"
    assert item.reuse_gloss_id == "g-existing"


def test_create_decision_parses() -> None:
    item = CreateGlossDecision.model_validate(
        {"tokenId": "t-2", "newGloss": {"pinyin": "jiàng", "gloss": "general; commander"}},
    )
    assert item.new_gloss.pinyin == "jiàng"


def test_gloss_response_rejects_both_reuse_and_new() -> None:
    with pytest.raises(ValidationError):
        GlossResponse.model_validate(
            {
                "decisions": [
                    {
                        "tokenId": "t-1",
                        "reuseGlossId": "g-1",
                        "newGloss": {"pinyin": "x", "gloss": "y"},
                    },
                ],
            },
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/models/test_gloss_response_models.py -v`  
Expected: FAIL — module not found

- [ ] **Step 3: Implement wire models**

```python
# packages/wenyan-models/src/wenyan_models/llm/gloss.py
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG


class NewGlossPayload(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG
    pinyin: str
    gloss: str


class ReuseGlossDecision(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG
    kind: Literal["reuse"] = "reuse"
    token_id: str = Field(alias="tokenId")
    reuse_gloss_id: str = Field(alias="reuseGlossId")


class CreateGlossDecision(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG
    kind: Literal["create"] = "create"
    token_id: str = Field(alias="tokenId")
    new_gloss: NewGlossPayload = Field(alias="newGloss")


GlossDecisionWire = Annotated[ReuseGlossDecision | CreateGlossDecision, Field(discriminator="kind")]


class GlossResponse(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG
    decisions: tuple[GlossDecisionWire, ...]
```

Use a `kind` discriminator so forced-tool JSON Schema can express `oneOf` cleanly.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git add packages/wenyan-models/src/wenyan_models/llm/ tests/models/test_gloss_response_models.py
git commit -m "feat: add gloss LLM wire response models"
```

### Task 2: Wire → artifact assembler

**Files:**
- Create: `src/wenyan/core/gloss/assemble_glosses.py`
- Test: `tests/core/gloss/test_assemble_glosses.py`

- [ ] **Step 1: Write failing assembler tests**

```python
# tests/core/gloss/test_assemble_glosses.py
from wenyan.core.gloss.assemble_glosses import assemble_glosses_artifact
from wenyan_models.artifacts.segment import GlossEntry, TokenizationArtifact
from wenyan_models.llm.gloss import CreateGlossDecision, GlossResponse, NewGlossPayload, ReuseGlossDecision


def test_assemble_mints_ids_for_new_glosses() -> None:
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "pending",
            "inputHash": "sha256:x",
            "attempts": 1,
            "text": "將",
            "tokens": [{"id": "t-jiang", "surface": "將", "start": 0, "end": 1}],
        },
    )
    response = GlossResponse(
        decisions=(
            CreateGlossDecision(
                token_id="t-jiang",
                new_gloss=NewGlossPayload(pinyin="jiàng", gloss="general; commander"),
            ),
        ),
    )
    artifact = assemble_glosses_artifact(response, tokenization, ())
    assert len(artifact.gloss_decisions) == 1
    assert artifact.gloss_decisions[0].decision == "create-new"
    assert artifact.gloss_decisions[0].gloss_id == artifact.new_glosses[0].id
    assert artifact.new_glosses[0].surface == "將"


def test_assemble_reuses_candidate_id() -> None:
    existing = GlossEntry(id="g-bu", surface="不", pinyin="bù", gloss="not; no")
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "pending",
            "inputHash": "sha256:x",
            "attempts": 1,
            "text": "不",
            "tokens": [{"id": "t-bu", "surface": "不", "start": 0, "end": 1}],
        },
    )
    response = GlossResponse(
        decisions=(ReuseGlossDecision(token_id="t-bu", reuse_gloss_id="g-bu"),),
    )
    artifact = assemble_glosses_artifact(response, tokenization, (existing,))
    assert artifact.gloss_decisions[0].gloss_id == "g-bu"
    assert artifact.new_glosses == ()
```

- [ ] **Step 2: Run test — FAIL**

- [ ] **Step 3: Implement assembler**

```python
# src/wenyan/core/gloss/assemble_glosses.py
import uuid

from wenyan.core.gloss.glossary_draft import normalize_gloss_reuse
from wenyan_models.artifacts.segment import (
    GlossDecision,
    GlossEntry,
    GlossesArtifact,
    TokenizationArtifact,
)
from wenyan_models.llm.gloss import CreateGlossDecision, GlossResponse, ReuseGlossDecision


def assemble_glosses_artifact(
    response: GlossResponse,
    tokenization: TokenizationArtifact,
    candidates: tuple[GlossEntry, ...],
) -> GlossesArtifact:
    token_by_id = {token.id: token for token in tokenization.tokens}
    gloss_decisions: list[GlossDecision] = []
    new_glosses: list[GlossEntry] = []
    new_gloss_ids: list[str] = []
    for item in response.decisions:
        if isinstance(item, ReuseGlossDecision):
            gloss_decisions.append(
                GlossDecision(
                    token_id=item.token_id,
                    gloss_id=item.reuse_gloss_id,
                    decision="reuse-existing",
                ),
            )
            continue
        assert isinstance(item, CreateGlossDecision)
        token = token_by_id[item.token_id]
        gloss_id = str(uuid.uuid4())
        new_glosses.append(
            GlossEntry(
                id=gloss_id,
                surface=token.surface,
                pinyin=item.new_gloss.pinyin,
                gloss=item.new_gloss.gloss,
            ),
        )
        new_gloss_ids.append(gloss_id)
        gloss_decisions.append(
            GlossDecision(
                token_id=item.token_id,
                gloss_id=gloss_id,
                decision="create-new",
            ),
        )
    glosses = GlossesArtifact(
        segment_id=tokenization.segment_id,
        model="pending",
        input_hash=tokenization.input_hash,
        attempts=1,
        gloss_decisions=tuple(gloss_decisions),
        new_gloss_ids=tuple(new_gloss_ids),
        new_glosses=tuple(new_glosses),
    )
    return normalize_gloss_reuse(glosses, tokenization, candidates)
```

Metadata fields (`segment_id`, `input_hash`, `model`, `attempts`) are placeholders overwritten by `stamp_segment_metadata` in `segment_runner`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

### Task 3: Plumb gloss job through wire model

**Files:**
- Modify: `src/wenyan/jobs/segment_runner.py`
- Modify: `src/wenyan/jobs/gloss_segment.py`
- Modify: `prompts/segment-gloss.md`
- Modify: `src/wenyan/core/adapters/mock_llm_client.py` (`_glosses`)
- Test: `tests/jobs/test_gloss_segment.py` (should pass unchanged)

- [ ] **Step 1: Extend `SegmentAnnotateJobSpec`**

Add optional fields to the dataclass:

```python
@dataclass(frozen=True)
class SegmentAnnotateJobSpec[TArtifact: BaseModel, TResponse: BaseModel = TArtifact]:
    prompt_name: str
    output_model: type[TArtifact]
    artifact_ref: Callable[[DocumentId, SegmentId], ArtifactRef]
    component_kind: ComponentKind
    skip_reason: str
    prepare: SegmentJobPrepare
    post_process: SegmentAnnotatePostProcess[TArtifact] | None = None
    response_model: type[TResponse] | None = None
    wire_to_artifact: Callable[..., TArtifact] | None = None
```

In `run_segment_annotate_job`, when `response_model` is set:

```python
wire_model = spec.response_model or spec.output_model
wire = ctx.llm.complete_model(prompt, wire_model)
if spec.wire_to_artifact is not None:
    artifact = spec.wire_to_artifact(wire, ctx, document_id, segment_id_value, input_hash)
else:
    artifact = wire  # type: ignore[assignment]
```

Remove `_post_process_gloss` calling `normalize_gloss_reuse` — assembly now owns dedupe.

- [ ] **Step 2: Update `_GLOSS_SPEC`**

```python
def _wire_gloss_to_artifact(
    response: GlossResponse,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    input_hash: ContentHash,
) -> GlossesArtifact:
    del input_hash
    tokenization = ctx.artifacts.read(
        segment_tokenization_ref(document_id, segment_id_value),
        TokenizationArtifact,
    )
    candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    return assemble_glosses_artifact(response, tokenization, candidates)


_GLOSS_SPEC = SegmentAnnotateJobSpec(
    prompt_name="segment-gloss",
    output_model=GlossesArtifact,
    response_model=GlossResponse,
    wire_to_artifact=_wire_gloss_to_artifact,
    ...
    post_process=None,
)
```

- [ ] **Step 3: Rewrite `prompts/segment-gloss.md`**

Remove lines asking for `segmentId`, `inputHash`, UUID v4 ids, `newGlossIds`, and `glossDecisions[].glossId` on create. Replace output section with:

```markdown
## Output

Return decisions only (schema from system instructions):

- One decision per token, in any order.
- Reuse: `{ "kind": "reuse", "tokenId": "…", "reuseGlossId": "<candidate id>" }`
- Create: `{ "kind": "create", "tokenId": "…", "newGloss": { "pinyin": "…", "gloss": "…" } }`
```

- [ ] **Step 4: Update `MockLLMClient._glosses`**

Return `GlossResponse` via `TypeAdapter(GlossResponse).validate_python(...)` with `kind` discriminator; drop artifact-shaped payload.

- [ ] **Step 5: Run gloss integration tests**

Run: `uv run python -m pytest tests/jobs/test_gloss_segment.py tests/core/gloss/ -q`  
Expected: PASS

- [ ] **Step 6: Commit**

### Task 4: Gloss semantic validators (prep for Phase 3)

**Files:**
- Create: `src/wenyan/core/gloss/validate_gloss_response.py`
- Test: `tests/core/gloss/test_validate_gloss_response.py`

- [ ] **Step 1: Tests for coverage and duplicate token ids**

```python
def test_validate_flags_missing_token() -> None:
    violations = validate_gloss_response(response, tokenization)
    assert any("t-missing" in v for v in violations)
```

- [ ] **Step 2: Implement `validate_gloss_response(response, tokenization) -> list[str]`**

Checks:
- Exactly one decision per `tokenization.tokens[].id`
- No decisions for unknown token ids
- `reuseGlossId` present in candidates when kind is reuse
- Pinyin contains a tone-marked vowel (simple regex: `[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]` or neutral `ü` forms)

Wire into gloss job in Phase 3; for Phase 1, unit-test only.

- [ ] **Step 3: Commit**

---

## Phase 2 — Forced tool use (Layer 2)

Single code path for Anthropic production and MiniMax dev.

### Task 5: API-safe JSON Schema builder

**Files:**
- Create: `src/wenyan/core/adapters/api_json_schema.py`
- Test: `tests/core/adapters/test_api_json_schema.py`

- [ ] **Step 1: Test that nested objects get `additionalProperties: false` and all properties required**

```python
from wenyan.core.adapters.api_json_schema import to_strict_json_schema
from wenyan_models.llm.gloss import GlossResponse

def test_strict_schema_marks_additional_properties_false() -> None:
    schema = to_strict_json_schema(GlossResponse)
    assert schema["additionalProperties"] is False
    assert "decisions" in schema["required"]
```

- [ ] **Step 2: Implement recursive post-processor over `model_json_schema()` output**

Walk `properties`, `items`, `oneOf`, `anyOf`, `$defs`; set `additionalProperties: false` on every `type: object`; promote every key in `properties` to `required`. Strip `$schema`, `title` if provider rejects them.

- [ ] **Step 3: Commit**

### Task 6: Forced tool request/response parsing

**Files:**
- Create: `src/wenyan/core/adapters/forced_tool_output.py`
- Modify: `src/wenyan/core/adapters/structured_output.py`

- [ ] **Step 1: Add `tool_name_for_model(model) -> str`**

e.g. `emit_gloss_response` from `GlossResponse.__name__` via camelCase.

- [ ] **Step 2: `build_forced_tool(model) -> dict`**

```python
def build_forced_tool(model: type[BaseModel], *, strict: bool = True) -> dict:
    name = tool_name_for_model(model)
    return {
        "name": name,
        "description": f"Emit structured {name} output.",
        "input_schema": to_strict_json_schema(model),
        **({"strict": True} if strict else {}),
    }
```

- [ ] **Step 3: `parse_tool_use_payload(payload: dict, model: type[T]) -> T`**

Find first `content[]` block with `type == "tool_use"` and matching name; `TypeAdapter(model).validate_python(block["input"])`. Raise `LLMParseError` if missing.

- [ ] **Step 4: Slim `build_structured_system_prompt`**

Remove full schema dump and echo-field rules. Keep task-agnostic guidance (Classical Chinese assistant, exact substrings, review status literals). Schema enforcement moves to the tool.

- [ ] **Step 5: Tests with synthetic API payloads — commit**

### Task 7: Switch `AnthropicLLMClient` to forced tools

**Files:**
- Modify: `src/wenyan/core/adapters/anthropic_llm_client.py`
- Modify: `tests/core/adapters/test_anthropic_llm_client.py`
- Modify: `tests/core/adapters/test_minimax_llm_client.py`

- [ ] **Step 1: Change request body**

```python
tool = build_forced_tool(model)
request_json = {
    "model": self._model,
    "max_tokens": 8192,
    "system": build_structured_system_prompt(model),
    "messages": [{"role": "user", "content": prompt.render()}],
    "tools": [tool],
    "tool_choice": {"type": "tool", "name": tool["name"]},
}
```

- [ ] **Step 2: Parse `tool_use` instead of `text` + `extract_json_text`**

Keep `parse_model_json` path behind a feature flag or delete once mock client also returns tool-shaped fixtures (mock can bypass HTTP and validate Python objects directly).

- [ ] **Step 3: Update httpx mock tests**

Fake response:

```python
{"content": [{"type": "tool_use", "id": "tu_1", "name": "emit_sampleModel", "input": {"answer": "ok"}}]}
```

- [ ] **Step 4: Run adapter tests — commit**

### Task 8 (optional hardening): Per-request `reuseGlossId` enum

**Depends on:** Phase 0 surface filtering (keeps enum small enough for Anthropic grammar limits).

**Files:**
- Modify: `src/wenyan/core/adapters/api_json_schema.py` or gloss-specific builder
- Modify: `src/wenyan/jobs/gloss_segment.py` — pass candidate ids into schema override

Build `GlossResponse` schema with `reuseGlossId.enum = [c.id for c in filtered_candidates]`. Skip if enum length risks Anthropic 400 "grammar too large"; log and fall back to unconstrained string.

---

## Phase 3 — Feedback retry loop (Layer 3)

### Task 9: Semantic validation errors and conversation refeed

**Files:**
- Modify: `src/wenyan/core/ports/llm_client.py`
- Modify: `src/wenyan/core/adapters/anthropic_llm_client.py`
- Modify: `src/wenyan/jobs/segment_runner.py`

- [ ] **Step 1: Add types**

```python
class LLMSemanticValidationError(LLMParseError):
    def __init__(self, violations: tuple[str, ...]) -> None:
        self.violations = violations
        super().__init__("; ".join(violations))


type SemanticValidator[T] = Callable[[T], tuple[str, ...]]
```

- [ ] **Step 2: Extend `complete_model` signature**

```python
def complete_model[T: BaseModel](
    self,
    prompt: StructuredPrompt,
    model: type[T],
    *,
    validate: SemanticValidator[T] | None = None,
) -> T: ...
```

- [ ] **Step 3: Implement conversation loop in client**

```python
messages = [{"role": "user", "content": prompt.render()}]
for attempt in range(self._retry.max_attempts):
    payload = post_messages(messages, ...)
    parsed = parse_tool_use_payload(payload, model)
    if validate is None:
        return parsed
    violations = validate(parsed)
    if not violations:
        return parsed
    messages.append({"role": "assistant", "content": payload["content"]})
    messages.append({
        "role": "user",
        "content": "Your output failed validation:\n- "
        + "\n- ".join(violations)
        + "\n\nFix and re-emit.",
    })
raise LLMSemanticValidationError(violations)
```

Distinguish **transient HTTP retries** (same request, backoff) from **semantic retries** (extend messages). Transient retries should not consume semantic attempt budget; nest loops or use separate counters.

- [ ] **Step 4: Pass gloss validator from `run_segment_annotate_job`**

Add optional `semantic_validate` to `SegmentAnnotateJobSpec`; gloss spec wires `validate_gloss_response` (needs tokenization — load in a closure in `gloss_segment.py`).

- [ ] **Step 5: Track real attempt count**

Update `stamp_segment_metadata` to accept `attempts: int` from client return metadata or a side channel.

- [ ] **Step 6: Tests**

- Mock client returns under-coverage wire response → refeed → second response passes.
- Assert assistant+user turns appended once.
- Assert `LLMSemanticValidationError` after max attempts.

- [ ] **Step 7: Commit**

### Task 10: Stop blind parse retries

- [ ] Remove the branch that re-posts identical prompt on `LLMParseError` without feedback (or limit to single transient parse retry only when no tool block returned).
- [ ] Update `test_does_not_retry_parse_errors` → `test_refeeds_on_semantic_validation_failure`.

---

## Phase 4 — Roll out to remaining LLM jobs

Apply the same pattern job-by-job. Suggested order (risk × call volume):

| Job | Wire model idea | Assembler notes |
| --- | --- | --- |
| `segment-tokenization` | `{ tokens: [{surface, start, end}] }` | Code assigns token UUIDs; copies `text` from input |
| `segment-grammar` | notes without ids | Code mints note ids; maps anchor token ids from tokenization |
| `segment-*-review` | drop echo fields; keep `status` + `findings` | Findings reference anchors by token id only |
| `paragraph-segmentation` | segment texts + ordinals only | Code assigns segment UUIDs |
| `paragraph-structure` | titles + spans | Code assigns paragraph ids |
| `chapter-structure` | chapter titles + spans | Code assigns chapter ids |
| `segment-context` | notes without ids (when CLI lands) | Same as grammar |

Per job task bundle (repeat ~6 tasks each):
1. Wire model in `wenyan_models/llm/`
2. Assembler in `src/wenyan/core/<domain>/`
3. Semantic validator (if any)
4. `SegmentAnnotateJobSpec` / job module wiring
5. Prompt trim (remove echo + id minting instructions)
6. Mock client + fixture update + job test

**Do not migrate** `MockLLMClient` generic JSON fixtures until wire shape exists — update handlers per template.

---

## Documentation updates

After Phase 1 lands:
- [ ] `architecture/preprocessing/model-strategy.md` — document wire vs artifact schema split under "LLM Call Contracts"
- [ ] `architecture/coding-style.md` — one row in the ports table for wire models
- [ ] `docs/code-audit.md` — mark gloss linking item resolved (reference gloss wire schema)
- [ ] `AGENTS.md` — no change required

After Phase 2:
- [ ] `architecture/tech-stack/cli.md` — note forced tool use for structured output

---

## Verification gate (each phase)

```bash
uv run ruff check packages/wenyan-models/src src/wenyan tests
uv run mypy packages/wenyan-models/src src/wenyan
uv run python -m pytest
```

Phase 1 narrow:

```bash
uv run python -m pytest tests/models/test_gloss_response_models.py tests/core/gloss/ tests/jobs/test_gloss_segment.py -q
```

---

## Risk notes

| Risk | Mitigation |
| --- | --- |
| Anthropic schema too large (400) | Slim wire models; strip echo fields; gloss enum only after candidate filtering |
| MiniMax tool strictness weaker than Anthropic | Same tool path; keep semantic validators (Layer 3) |
| Breaking existing preprocess artifacts | Wire change only affects new LLM calls; on-disk `GlossesArtifact` shape unchanged |
| `SegmentAnnotateJobSpec` generic complexity | Default `response_model=None` preserves old path until each job migrates |

---

## Suggested PR slicing

1. **PR 0 (Phase 0):** Surface-filtered prompt candidates — token-cost win, no artifact shape change.
2. **PR 1 (Phase 1):** Gloss wire model + assembler + job plumbing + prompt + mock — fixes linking bug, still free-text JSON path.
3. **PR 2 (Phase 2):** Forced tool use infrastructure + client switch — all jobs benefit immediately for JSON syntax.
4. **PR 3 (Phase 3):** Semantic feedback retry + gloss validator wired.
5. **PR 4+ (Phase 4):** One PR per job family (tokenization, grammar, reviews, structure).
