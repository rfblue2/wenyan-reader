# Paragraph Assembly Implementation Plan

> **Update (2026-06-29):** LLM `review-paragraph-assembly` was removed post-implementation. Assembly is `assemble-paragraph` only.

**Goal:** Implement `assemble-paragraph` so completed segment subjobs compile into a reader-shaped `package.json` under preprocess, with deterministic validation and updated paragraph status rollups.

**Architecture:** Add reader paragraph Pydantic models and a pure `compile_paragraph_package()` transformer in `core/assembly/`. Two job modules mirror segment draft/review jobs. Assembly artifacts stay in `preprocess/.../jobs/assembly/<paragraph-id>/` until a future `package-document` slice promotes them to `content/`. Status derivation treats assembly as two paragraph-level components and stops marking paragraphs complete when segments alone are done.

**Tech Stack:** Python 3.12+, Pydantic v2, Typer CLI, pytest via `uv run python -m pytest`, existing `ArtifactStore` / `JobContext` / `MockLLMClient` patterns.

**Spec:** [2026-06-29-paragraph-assembly-design.md](../specs/2026-06-29-paragraph-assembly-design.md)

---

## File map

| File | Responsibility |
| --- | --- |
| `packages/wenyan-models/src/wenyan_models/reader/paragraph.py` | Reader paragraph schema (`ParagraphPackage`, etc.) |
| `packages/wenyan-models/src/wenyan_models/artifacts/assembly.py` | Assembly validation + review artifact models |
| `packages/wenyan-models/src/wenyan_models/domain/enums.py` | `PARAGRAPH_ASSEMBLY_PACKAGE`, assembly `ComponentKind` values |
| `packages/wenyan-models/src/wenyan_models/status/paragraph.py` | `ParagraphAssemblyStatus` on `ParagraphStatus` |
| `src/wenyan/core/assembly/compile_paragraph.py` | Pure compile: segment artifacts → `ParagraphPackage` |
| `src/wenyan/core/assembly/input_hash.py` | Upstream hash for skip/stale |
| `src/wenyan/core/assembly/validate_package.py` | Deterministic validation checks |
| `src/wenyan/core/assembly/load_segment_outputs.py` | Load segment subjob artifacts for one segment |
| `src/wenyan/jobs/assemble_paragraph.py` | `run_assemble_paragraph` job |
| `src/wenyan/jobs/review_paragraph_assembly.py` | `run_review_paragraph_assembly` job |
| `src/wenyan/core/status/assembly.py` | Paragraph assembly component status helpers |
| `src/wenyan/core/run/stale_assembly.py` | Remove stale assembly dirs (called from prune) |
| `prompts/review-paragraph-assembly.md` | LLM review prompt |
| `tests/fixtures/llm/review-paragraph-assembly.json` | Mock approved review fixture |

---

### Task 1: Reader models and assembly artifact kinds

**Files:**
- Create: `packages/wenyan-models/src/wenyan_models/reader/__init__.py`
- Create: `packages/wenyan-models/src/wenyan_models/reader/paragraph.py`
- Create: `packages/wenyan-models/src/wenyan_models/artifacts/assembly.py`
- Modify: `packages/wenyan-models/src/wenyan_models/domain/enums.py`
- Modify: `packages/wenyan-models/src/wenyan_models/artifacts/__init__.py`
- Test: `tests/models/test_reader_paragraph_models.py`

- [ ] **Step 1: Write failing model tests**

```python
# tests/models/test_reader_paragraph_models.py
from wenyan_models.reader.paragraph import ParagraphPackage, ReaderNote, ReaderSegment, ReaderToken


def test_paragraph_package_roundtrip_minimal():
    payload = {
        "id": "c777d984-afd6-4a31-aa34-2d26d29fb445",
        "segments": [
            {
                "id": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
                "text": "孟子見梁惠王。",
                "newGlossIds": ["7d0d9c78-8307-4f11-9352-63b5d74af0fd"],
                "tokens": [
                    {
                        "id": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
                        "surface": "孟子",
                        "start": 0,
                        "end": 2,
                        "glossId": "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
                    }
                ],
                "notes": [],
            }
        ],
    }
    model = ParagraphPackage.model_validate(payload)
    assert model.segments[0].tokens[0].gloss_id == "7d0d9c78-8307-4f11-9352-63b5d74af0fd"
    roundtrip = ParagraphPackage.model_validate(model.model_dump(by_alias=True))
    assert roundtrip == model
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/models/test_reader_paragraph_models.py -v`  
Expected: FAIL (`ModuleNotFoundError: wenyan_models.reader`)

- [ ] **Step 3: Implement models**

`packages/wenyan-models/src/wenyan_models/reader/paragraph.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG, ParagraphIdField, SegmentIdField


class ReaderToken(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    surface: str
    start: int
    end: int
    gloss_id: str = Field(alias="glossId")


class ReaderNoteSource(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    label: str
    detail: str = ""


class ReaderNote(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    type: Literal["grammar", "context"]
    anchor_token_ids: tuple[str, ...] = Field(alias="anchorTokenIds")
    body: str
    sources: tuple[ReaderNoteSource, ...] = ()


class ReaderSegment(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: SegmentIdField
    text: str
    new_gloss_ids: tuple[str, ...] = Field(alias="newGlossIds")
    tokens: tuple[ReaderToken, ...]
    notes: tuple[ReaderNote, ...] = ()


class ParagraphPackage(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ParagraphIdField
    segments: tuple[ReaderSegment, ...]
```

`packages/wenyan-models/src/wenyan_models/artifacts/assembly.py`:

```python
from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ContentHashField,
    ParagraphIdField,
)
from wenyan_models.domain.enums import ReviewStatus, ValidationStatus
from wenyan_models.domain.validation import CheckResult


class ParagraphAssemblyValidationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    input_hash: ContentHashField = Field(alias="inputHash")
    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()


class ParagraphAssemblyReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()
    required_fixes: tuple[dict[str, object], ...] = Field(default=(), alias="requiredFixes")
```

Add to `domain/enums.py`:

```python
    PARAGRAPH_ASSEMBLY_PACKAGE = "paragraph-assembly-package"
```

Add to `ComponentKind`:

```python
    ASSEMBLE_PARAGRAPH = "assemble-paragraph"
    REVIEW_PARAGRAPH_ASSEMBLY = "review-paragraph-assembly"
```

Export new models from `artifacts/__init__.py` and `reader/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/models/test_reader_paragraph_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/wenyan-models/src/wenyan_models/reader/ \
  packages/wenyan-models/src/wenyan_models/artifacts/assembly.py \
  packages/wenyan-models/src/wenyan_models/domain/enums.py \
  packages/wenyan-models/src/wenyan_models/artifacts/__init__.py \
  tests/models/test_reader_paragraph_models.py
git commit -m "feat: add reader paragraph and assembly artifact models"
```

---

### Task 2: Artifact refs and paths for `package.json`

**Files:**
- Modify: `src/wenyan/core/ports/artifact_ref.py`
- Modify: `src/wenyan/core/adapters/paths.py`
- Modify: `tests/core/ports/test_artifact_ref.py`

- [ ] **Step 1: Write failing ref test**

Add to `tests/core/ports/test_artifact_ref.py`:

```python
        (
            lambda: refs.paragraph_assembly_package_ref(DOC, PARAGRAPH),
            ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE,
        ),
```

And assert path ends with `jobs/assembly/{paragraph}/package.json`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/core/ports/test_artifact_ref.py -v -k package`  
Expected: FAIL (`paragraph_assembly_package_ref` not defined)

- [ ] **Step 3: Implement ref + path**

In `artifact_ref.py` `_SCOPES`:

```python
    ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE: _PARAGRAPH_SCOPE,
```

Add function:

```python
def paragraph_assembly_package_ref(
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE,
        document_id=document_id,
        paragraph_id=paragraph_id,
    )
```

In `paths.py` before `PARAGRAPH_ASSEMBLY_VALIDATION` case:

```python
        case ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE:
            paragraph_id = _require(ref.paragraph_id, ref.kind, "paragraph_id")
            return root / "jobs" / "assembly" / str(paragraph_id) / "package.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/core/ports/test_artifact_ref.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wenyan/core/ports/artifact_ref.py src/wenyan/core/adapters/paths.py tests/core/ports/test_artifact_ref.py
git commit -m "feat: add paragraph assembly package artifact ref"
```

---

### Task 3: Compile paragraph package (TDD)

**Files:**
- Create: `src/wenyan/core/assembly/__init__.py`
- Create: `src/wenyan/core/assembly/compile_paragraph.py`
- Create: `src/wenyan/core/assembly/load_segment_outputs.py`
- Create: `tests/core/assembly/test_compile_paragraph.py`
- Create: `tests/fixtures/assembly/minimal-segment-outputs.json` (inline in test is fine)

- [ ] **Step 1: Write failing compile tests**

```python
# tests/core/assembly/test_compile_paragraph.py
from wenyan.core.assembly.compile_paragraph import compile_paragraph_package
from wenyan.core.assembly.load_segment_outputs import CompiledSegmentInputs
from wenyan_models.artifacts.paragraph import ParagraphDraft, ParagraphDraftSegment
from wenyan_models.artifacts.segment import (
    ContextNoteItem,
    ContextNotesArtifact,
    GlossDecision,
    GlossesArtifact,
    GrammarNoteItem,
    GrammarNotesArtifact,
    TokenItem,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import paragraph_id, segment_id


def test_compile_joins_tokens_glosses_and_notes():
    seg = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")
    token_id = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
    gloss_id = "7d0d9c78-8307-4f11-9352-63b5d74af0fd"
    draft = ParagraphDraft.model_validate(
        {
            "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
            "model": "test",
            "inputHash": "sha256:test",
            "attempts": 1,
            "segments": [{"id": str(seg), "text": "孟子見梁惠王。"}],
        }
    )
    outputs = (
        CompiledSegmentInputs(
            segment_id=seg,
            text="孟子見梁惠王。",
            tokenization=TokenizationArtifact.model_validate(
                {
                    "segmentId": str(seg),
                    "model": "test",
                    "inputHash": "sha256:t",
                    "attempts": 1,
                    "text": "孟子見梁惠王。",
                    "tokens": [{"id": token_id, "surface": "孟子", "start": 0, "end": 2}],
                }
            ),
            glosses=GlossesArtifact.model_validate(
                {
                    "segmentId": str(seg),
                    "model": "test",
                    "inputHash": "sha256:g",
                    "attempts": 1,
                    "glossDecisions": [
                        {"tokenId": token_id, "glossId": gloss_id, "decision": "reuse-existing"}
                    ],
                    "newGlossIds": [gloss_id],
                    "newGlosses": [],
                }
            ),
            grammar_notes=GrammarNotesArtifact.model_validate(
                {
                    "segmentId": str(seg),
                    "model": "test",
                    "inputHash": "sha256:gr",
                    "attempts": 1,
                    "grammarNotes": [
                        {
                            "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
                            "anchorTokenIds": [token_id],
                            "body": "Grammar note.",
                        }
                    ],
                }
            ),
            context_notes=ContextNotesArtifact.model_validate(
                {
                    "segmentId": str(seg),
                    "model": "test",
                    "inputHash": "sha256:cn",
                    "attempts": 1,
                    "contextNotes": [
                        {
                            "id": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
                            "anchorTokenIds": [token_id],
                            "body": "Context note.",
                            "sources": [{"label": "Mencius 1A1", "excerpt": "detail text"}],
                        }
                    ],
                }
            ),
        ),
    )
    package = compile_paragraph_package(draft, outputs)
    segment = package.segments[0]
    assert segment.tokens[0].gloss_id == gloss_id
    assert segment.new_gloss_ids == (gloss_id,)
    assert len(segment.notes) == 2
    assert segment.notes[0].type == "grammar"
    assert segment.notes[1].type == "context"
    assert segment.notes[1].sources[0].detail == "detail text"
```

Add a second test `test_compile_folds_paragraph_context_notes` with `paragraphContextNotes` anchoring a segment id.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/core/assembly/test_compile_paragraph.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement compile**

`load_segment_outputs.py`:

```python
from dataclasses import dataclass

from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import SegmentId


@dataclass(frozen=True)
class CompiledSegmentInputs:
    segment_id: SegmentId
    text: str
    tokenization: TokenizationArtifact
    glosses: GlossesArtifact
    grammar_notes: GrammarNotesArtifact
    context_notes: ContextNotesArtifact
```

`compile_paragraph.py` — implement `compile_paragraph_package()`:

- Build `gloss_id` map from `glosses.gloss_decisions`
- Map tokens to `ReaderToken` with `glossId`
- Convert grammar notes → `ReaderNote(type="grammar")`
- Convert context notes → `ReaderNote(type="context")` with sources `{label, detail}` using `detail` or `excerpt`
- For each `paragraphContextNotes` entry in draft: find target segment by first `anchorSegmentIds` entry; pick token with minimum `start`; append context note

Return `ParagraphPackage(id=draft.paragraph_id, segments=...)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/core/assembly/test_compile_paragraph.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wenyan/core/assembly/ tests/core/assembly/
git commit -m "feat: compile segment artifacts into reader paragraph package"
```

---

### Task 4: Assembly input hash and validation

**Files:**
- Create: `src/wenyan/core/assembly/input_hash.py`
- Create: `src/wenyan/core/assembly/validate_package.py`
- Create: `tests/core/assembly/test_assembly_input_hash.py`
- Create: `tests/core/assembly/test_validate_package.py`

- [ ] **Step 1: Write failing validation test**

```python
def test_validate_package_rejects_missing_gloss_on_token():
    # build minimal ParagraphPackage with token missing gloss resolution
    # call validate_paragraph_package(draft, outputs, package)
    # assert ValidationStatus.FAILED and check name token-gloss-coverage
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/core/assembly/test_validate_package.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

`input_hash.py`:

```python
def assembly_input_hash(
    draft: ParagraphDraft,
    segment_output_hashes: dict[str, str],
) -> str:
    payload = {
        "draft": draft.model_dump(by_alias=True, mode="json"),
        "segments": segment_output_hashes,
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))
```

Compute per-segment hash from concatenated artifact JSON dumps (tokenization, glosses, grammar-notes, context-notes).

`validate_package.py`:

```python
def validate_paragraph_package(
    draft: ParagraphDraft,
    outputs: Sequence[CompiledSegmentInputs],
    package: ParagraphPackage,
) -> ParagraphAssemblyValidationArtifact:
    checks: list[CheckResult] = []
    # segment-order, reconstruction, token offsets, gloss coverage, note anchors, schema
    status = ValidationStatus.PASSED if all(c.passed for c in checks) else ValidationStatus.FAILED
    return ParagraphAssemblyValidationArtifact(...)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/core/assembly/ -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wenyan/core/assembly/input_hash.py src/wenyan/core/assembly/validate_package.py tests/core/assembly/
git commit -m "feat: add paragraph assembly input hash and validation"
```

---

### Task 5: `assemble-paragraph` job

**Files:**
- Create: `src/wenyan/jobs/assemble_paragraph.py`
- Create: `tests/jobs/test_assemble_paragraph.py`
- Create: `tests/conftest.py` helper (or `tests/jobs/assembly_helpers.py`)

- [ ] **Step 1: Add test helper to finish all eight subjobs for a paragraph**

```python
# tests/jobs/assembly_helpers.py
def prepare_paragraph_with_complete_segments(tmp_workspace: Path) -> tuple[JobContext, DocumentId, ParagraphId]:
    # ingest sunzi → chapter proposal → split_paragraphs → split_segments
    # for EACH segment in draft: run all 8 segment subjobs (reuse run_preprocess loop or call each runner)
    ...
```

- [ ] **Step 2: Write failing job test**

```python
def test_assemble_paragraph_writes_package_and_validation(tmp_workspace: Path):
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    outcome = run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    assert outcome_exit_code(outcome) == 0
    package_ref = paragraph_assembly_package_ref(doc_id, paragraph_id_value)
    validation_ref = paragraph_assembly_validation_ref(doc_id, paragraph_id_value)
    assert ctx.artifacts.exists(package_ref)
    assert ctx.artifacts.exists(validation_ref)
    package = ctx.artifacts.read(package_ref, ParagraphPackage)
    assert package.segments
```

Add tests: `test_assemble_paragraph_skips_current`, `test_assemble_paragraph_blocked_upstream`, `test_assemble_paragraph_missing_draft`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/jobs/test_assemble_paragraph.py -v`  
Expected: FAIL

- [ ] **Step 4: Implement job**

`assemble_paragraph.py` outline:

```python
def run_assemble_paragraph(ctx, document_id, paragraph_id_value, options) -> JobOutcome[ParagraphPackage]:
    draft_ref = paragraph_draft_ref(document_id, paragraph_id_value)
    if not ctx.artifacts.exists(draft_ref):
        return JobFailure(code="missing-input", message="paragraph draft is missing")
    draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
    for segment in draft.segments:
        if pending_segment_subjobs(ctx.artifacts, document_id, segment.id):
            return JobFailure(code="blocked-upstream", message=f"segment {segment.id} is incomplete")
    outputs = load_all_segment_outputs(ctx.artifacts, document_id, draft)
    input_hash = compute_assembly_input_hash(draft, outputs)
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id_value)
    validation_ref = paragraph_assembly_validation_ref(document_id, paragraph_id_value)
    if ctx.artifacts.exists(package_ref) and ctx.artifacts.exists(validation_ref) and not options.force:
        existing = ctx.artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
        if existing.input_hash == input_hash and existing.status == ValidationStatus.PASSED:
            return Skipped(reason="paragraph assembly is current")
    package = compile_paragraph_package(draft, outputs)
    validation = validate_paragraph_package(draft, outputs, package)
    if validation.status == ValidationStatus.FAILED:
        if not options.dry_run:
            ctx.artifacts.write(validation_ref, validation, dry_run=False)
        return JobFailure(code="validation-failed", message="paragraph assembly validation failed")
    if options.dry_run:
        return Promoted(artifact=package)
    ctx.artifacts.write_batch([
        ArtifactWrite(ref=package_ref, payload=package),
        ArtifactWrite(ref=validation_ref, payload=validation),
    ], dry_run=False)
    return Promoted(artifact=package)
```

Implement `load_all_segment_outputs()` in `load_segment_outputs.py` using artifact refs; require each of the four draft artifacts to exist.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/jobs/test_assemble_paragraph.py -v`  
Expected: PASS (may take ~30s with mock LLM for all segments)

- [ ] **Step 6: Commit**

```bash
git add src/wenyan/jobs/assemble_paragraph.py tests/jobs/test_assemble_paragraph.py tests/jobs/assembly_helpers.py
git commit -m "feat: implement assemble-paragraph job"
```

---

### Task 6: `review-paragraph-assembly` job + prompt + mock fixture

**Files:**
- Create: `src/wenyan/jobs/review_paragraph_assembly.py`
- Create: `prompts/review-paragraph-assembly.md`
- Create: `tests/fixtures/llm/review-paragraph-assembly.json`
- Modify: `src/wenyan/core/adapters/mock_llm_client.py`
- Modify: `tests/prompts/test_prompt_templates.py`
- Create: `tests/jobs/test_review_paragraph_assembly.py`

- [ ] **Step 1: Write failing review test**

```python
def test_review_paragraph_assembly_approves(tmp_workspace: Path):
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    outcome = run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    assert outcome_exit_code(outcome) == 0
    review = ctx.artifacts.read(
        paragraph_assembly_review_ref(doc_id, paragraph_id_value),
        ParagraphAssemblyReviewArtifact,
    )
    assert review.status == ReviewStatus.APPROVED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/jobs/test_review_paragraph_assembly.py -v`  
Expected: FAIL

- [ ] **Step 3: Add prompt and fixture**

`prompts/review-paragraph-assembly.md` — mirror `segment-gloss-review.md` structure with checklist from spec; context keys:

- `paragraph_id`
- `review_input_hash`
- `paragraph_package_json`
- `paragraph_draft_json`

`tests/fixtures/llm/review-paragraph-assembly.json`:

```json
{
  "paragraphId": "00000000-0000-0000-0000-000000000001",
  "model": "mock",
  "inputHash": "sha256:mock",
  "attempts": 1,
  "status": "approved",
  "findings": [],
  "requiredFixes": []
}
```

In `mock_llm_client.py` `complete_model`, the generic fixture fallback already handles unknown templates if `{name}.json` exists — verify template name matches file stem `review-paragraph-assembly`.

- [ ] **Step 4: Implement review job**

Mirror `review_segment_gloss.py`:

```python
def run_review_paragraph_assembly(ctx, document_id, paragraph_id_value, options):
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id_value)
    if not ctx.artifacts.exists(package_ref):
        return JobFailure(code="missing-input", message="paragraph assembly package is missing")
    package = ctx.artifacts.read(package_ref, ParagraphPackage)
    input_hash = sha256_text(package.model_dump_json(by_alias=True))
    review_ref = paragraph_assembly_review_ref(document_id, paragraph_id_value)
    if ctx.artifacts.exists(review_ref) and not options.force:
        existing = ctx.artifacts.read(review_ref, ParagraphAssemblyReviewArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="paragraph assembly review is current")
    template = load_prompt_template(ctx.repo_root / ctx.config.prompts.root, "review-paragraph-assembly")
    draft = ctx.artifacts.read(paragraph_draft_ref(document_id, paragraph_id_value), ParagraphDraft)
    context = {
        "paragraph_id": str(paragraph_id_value),
        "review_input_hash": str(input_hash),
        "paragraph_package_json": package.model_dump_json(by_alias=True),
        "paragraph_draft_json": draft.model_dump_json(by_alias=True),
    }
    review = ctx.llm.complete_model(RenderedPrompt(template, context), ParagraphAssemblyReviewArtifact)
    review = review.model_copy(update={
        "paragraph_id": paragraph_id_value,
        "input_hash": input_hash,
        "model": ctx.config.models.active_model,
        "attempts": 1,
    })
    ...
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/jobs/test_review_paragraph_assembly.py tests/prompts/test_prompt_templates.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/wenyan/jobs/review_paragraph_assembly.py prompts/review-paragraph-assembly.md \
  tests/jobs/test_review_paragraph_assembly.py tests/fixtures/llm/review-paragraph-assembly.json \
  tests/prompts/test_prompt_templates.py
git commit -m "feat: implement review-paragraph-assembly job"
```

---

### Task 7: CLI wiring

**Files:**
- Modify: `src/wenyan/cli/preprocess.py`

- [ ] **Step 1: Write failing CLI smoke test (optional but recommended)**

```python
# tests/cli/test_assemble_paragraph_cli.py
from typer.testing import CliRunner
from wenyan.cli.main import app

def test_assemble_paragraph_cli_not_stub(tmp_workspace, monkeypatch):
    # prepare workspace + complete segments; invoke CLI; assert exit 0
```

- [ ] **Step 2: Replace stubs with real handlers**

```python
@preprocess_app.command("assemble-paragraph")
def assemble_paragraph_cmd(..., force: ForceOption = False, dry_run: DryRunOption = False):
    ctx, doc_id = resolve_document_context(document)
    paragraph_id_value = resolve_paragraph_id(...)
    outcome = run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions(force=force, dry_run=dry_run))
    raise_on_failure(outcome)
    emit_outcome(outcome)

@preprocess_app.command("review-paragraph-assembly")
def review_paragraph_assembly_cmd(...):
    ...
```

Follow existing command patterns for `resolve_paragraph_id`, exit codes, and `--force` / `--dry-run`.

- [ ] **Step 3: Run CLI test**

Run: `uv run python -m pytest tests/cli/test_assemble_paragraph_cli.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/wenyan/cli/preprocess.py tests/cli/test_assemble_paragraph_cli.py
git commit -m "feat: wire assemble-paragraph and review-paragraph-assembly CLI commands"
```

---

### Task 8: Paragraph status derivation and terminal output

**Files:**
- Modify: `packages/wenyan-models/src/wenyan_models/status/paragraph.py`
- Create: `src/wenyan/core/status/assembly.py`
- Modify: `src/wenyan/core/status/derivation.py`
- Modify: `src/wenyan/cli/status_output.py`
- Modify: `tests/core/adapters/test_filesystem_status_reader.py`
- Create: `tests/core/status/test_paragraph_assembly_status.py`

- [ ] **Step 1: Write failing status tests**

```python
def test_paragraph_not_complete_when_segments_done_but_assembly_pending(tmp_workspace):
    ctx, doc_id, _, paragraph_id_value, _ = prepare_all_eight_subjobs_first_segment_only(...)
    # run remaining subjobs for all segments OR use helper that completes one segment only
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)
    assert payload.assembly.assemble.status == UnitStatus.PENDING
    assert _rollup_paragraph_status(payload) != UnitStatus.COMPLETE  # via exported helper or indirect via item status

def test_paragraph_complete_after_assembly_and_review(tmp_workspace):
    ...
    run_assemble_paragraph(...)
    run_review_paragraph_assembly(...)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)
    assert payload.assembly.review.status == UnitStatus.COMPLETE
```

Add `ParagraphAssemblyStatus` to `status/paragraph.py`:

```python
class ParagraphAssemblyStatus(BaseModel):
    assemble: ComponentStatusItem
    review: ComponentStatusItem

class ParagraphStatus(BaseModel):
    ...
    assembly: ParagraphAssemblyStatus | None = None
```

Implement `derive_paragraph_assembly_status()` in `core/status/assembly.py`:

- assemble complete when `package.json` + passed `validation.json` with current input hash
- assemble stale when validation hash mismatches upstream
- review complete when approved review matches package hash
- review blocked when rejected

Update `_rollup_paragraph_status` in `derivation.py` per spec rollup table.

Update `_render_paragraph` in `status_output.py` to print Assembly section.

- [ ] **Step 2: Run status tests**

Run: `uv run python -m pytest tests/core/status/test_paragraph_assembly_status.py tests/core/adapters/test_filesystem_status_reader.py -v`  
Expected: PASS (update existing tests if paragraph rollup expectations changed)

- [ ] **Step 3: Commit**

```bash
git add packages/wenyan-models/src/wenyan_models/status/paragraph.py \
  src/wenyan/core/status/assembly.py src/wenyan/core/status/derivation.py \
  src/wenyan/cli/status_output.py tests/core/status/ tests/core/adapters/test_filesystem_status_reader.py
git commit -m "feat: track paragraph assembly in status rollups"
```

---

### Task 9: Prune stale assembly artifacts

**Files:**
- Create: `src/wenyan/core/run/stale_assembly.py`
- Modify: `src/wenyan/jobs/prune_orphan_segments.py` (or `prune` CLI handler)
- Create: `tests/core/run/test_stale_assembly.py`

- [ ] **Step 1: Write failing prune test**

```python
def test_prune_removes_stale_assembly_after_orphan_segment_removed(tmp_workspace):
    # setup paragraph with assembly, remove a segment dir or run orphan prune after draft change
    # assert assembly dir deleted
```

- [ ] **Step 2: Implement**

```python
def prune_stale_assembly(artifacts, repo_root, document_id, *, dry_run: bool) -> tuple[str, ...]:
    # for each paragraph with draft: if assembly exists and assembly_input_hash != validation.input_hash
    # or upstream segment missing: shutil.rmtree(assembly dir)
```

Call from `run_prune_orphan_segments` after orphan removal (stale assembly for affected paragraphs).

- [ ] **Step 3: Run tests**

Run: `uv run python -m pytest tests/core/run/test_stale_assembly.py tests/core/run/test_orphan_segments.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/wenyan/core/run/stale_assembly.py src/wenyan/jobs/prune_orphan_segments.py tests/core/run/test_stale_assembly.py
git commit -m "feat: prune stale paragraph assembly artifacts"
```

---

### Task 10: Architecture docs and preprocessing skill

**Files:**
- Modify: `architecture/cli-spec.md`
- Modify: `architecture/preprocessing/intermediate-artifacts.md`
- Modify: `architecture/preprocessing/editor-workflow.md`
- Modify: `.cursor/skills/preprocessing-segments/SKILL.md`

- [ ] **Step 1: Update CLI spec**

- Split `assemble-paragraph` from review command
- Add `review-paragraph-assembly` command block
- Document `package.json` staging path
- Clarify `package-document` promotes approved packages (still stubbed)

- [ ] **Step 2: Update intermediate-artifacts.md**

Add `package.json` under `jobs/assembly/` and two-command flow diagram in Paragraph Assembly section.

- [ ] **Step 3: Update editor-workflow.md and skill**

Add steps after segment completion:

```shell
uv run wenyan preprocess assemble-paragraph <slug> --paragraph <paragraph-id>
uv run wenyan preprocess review-paragraph-assembly <slug> --paragraph <paragraph-id>
```

Mark assembly commands as implemented in skill table.

- [ ] **Step 4: Commit**

```bash
git add architecture/cli-spec.md architecture/preprocessing/intermediate-artifacts.md \
  architecture/preprocessing/editor-workflow.md .cursor/skills/preprocessing-segments/SKILL.md
git commit -m "docs: document paragraph assembly commands and artifacts"
```

---

### Task 11: Full verification

- [ ] **Step 1: Run full test suite**

Run: `uv run python -m pytest -q`  
Expected: all tests PASS within seconds (use `-x` if debugging)

- [ ] **Step 2: Manual smoke test on sunzi fixture (if real preprocess tree exists)**

```shell
uv run wenyan preprocess assemble-paragraph sunzi-bingfa --paragraph <id>
uv run wenyan preprocess review-paragraph-assembly sunzi-bingfa --paragraph <id>
uv run wenyan preprocess status sunzi-bingfa --paragraph <id>
```

Confirm Assembly section shows assemble + review complete.

---

## Spec coverage checklist

| Spec requirement | Task |
| --- | --- |
| Two commands (assemble + review) | Tasks 5, 6, 7 |
| `package.json` in preprocess | Tasks 1, 2, 5 |
| Deterministic compile | Task 3 |
| Validation artifact | Tasks 4, 5 |
| Review artifact | Task 6 |
| No write to `content/` | Tasks 5, 6 (by design) |
| Status rollup change | Task 8 |
| Stale/prune | Task 9 |
| Mock LLM tests | Tasks 5, 6 |
| Architecture docs | Task 10 |
| `package-document` contract documented | Task 10 (docs only) |
| `run preprocess` unchanged | No task (verify no changes in Task 11) |

## Out of scope (do not implement here)

- `package-document`
- `run preprocess` auto-advance to assembly
- `review-paragraph-structure` (separate stub)
