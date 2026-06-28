# Preprocessing CLI Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working preprocessing CLI vertical slice — ingest through segment tokenization review on `sunzi-bingfa`, plus `status` and `validate-artifacts` — with stubbed remaining commands.

**Architecture:** Ports-and-adapters layout. `wenyan-models` holds Pydantic models for artifacts, config, domain types, and status payloads (no I/O). `wenyan/core/ports/` defines `Protocol` interfaces; `wenyan/core/adapters/` implements them. `wenyan/jobs/` are application services that depend only on ports and models. CLI is a thin delivery mechanism. Strict mypy + pydantic plugin gates every task.

**Tech Stack:** Python 3.12+, uv, Typer, Rich, Pydantic v2, httpx, pytest, Ruff, mypy (strict)

## Global Constraints

- Workspace roots: `preprocess/documents/<document-id>/` for artifacts; `content/documents/<document-id>/` for reader package (slice does not write `content/` yet).
- Ingest accepts a source directory only (`sources/documents/<slug>/`).
- CLI accepts UUID or slug resolved via `sources/registry.yaml`.
- Validation reports are sibling `*.validation.json` files.
- Job metadata (`inputHash`, `promptVersion`, `model`, `attempts`) is embedded in each output artifact JSON.
- Review failure is fail-fast: non-zero exit, write review artifact, no auto-repair.
- Config resolution order: env vars → `.wenyan/config.yaml` or `WENYAN_CONFIG` → `config/preprocessing.yaml`.
- Slice LLM provider: Anthropic only, behind `LLMClient` port.
- `core/` must not import Typer; `wenyan-models` must not import CLI, LLM, or filesystem code.
- **Typing:** `mypy --strict` with `pydantic.mypy` plugin must pass on `packages/wenyan-models` and `src/wenyan/core` and `src/wenyan/jobs` before each task commit.
- **Pydantic:** structured data is `BaseModel` (see [Coding Style](../architecture/coding-style.md)); no manual JSON/YAML dict parsing for typed shapes.
- **Dependency rule:** `jobs/` → `core/ports` + `wenyan_models`; `core/adapters` → `core/ports` + `wenyan_models`; `cli/` → `jobs` + `core`; never `core/ports` → `core/adapters`.

## Type Architecture

Design for definitionally correct types first. Prefer making invalid states unrepresentable over runtime checks scattered through jobs.

### Layer diagram

```text
cli/                  Typer commands, exit codes, Rich/JSON output
  ↓
jobs/                 Application services (one per command)
  ↓
core/ports/           Protocol interfaces only — the "Java interfaces"
  ↓
core/adapters/        Filesystem, YAML registry, Anthropic, mock LLM
  ↓
wenyan_models/        Pydantic models, enums, branded types
```

### Branded IDs (newtypes)

Raw `str` must not cross API boundaries for entity IDs. Define in `wenyan_models/domain/ids.py`:

```python
from typing import NewType

DocumentId = NewType("DocumentId", str)
ChapterId = NewType("ChapterId", str)
ParagraphId = NewType("ParagraphId", str)
SegmentId = NewType("SegmentId", str)
Slug = NewType("Slug", str)
ContentHash = NewType("ContentHash", str)   # always "sha256:..."
PromptVersion = NewType("PromptVersion", str)
```

Helpers (same module):

```python
def document_id(value: str) -> DocumentId: ...
def parse_content_hash(value: str) -> ContentHash: ...  # validates prefix
```

Pydantic models use `Annotated[DocumentId, ...]` validators or wrap/unwrap at adapter boundaries only.

### Enums (closed sets)

`wenyan_models/domain/enums.py`:

```python
class ArtifactKind(StrEnum):
    NORMALIZED_DOCUMENT = "normalized-document"
    CHAPTER_PROPOSAL = "chapter-proposal"
    CHAPTER_PROPOSAL_VALIDATION = "chapter-proposal-validation"
  # ... one variant per on-disk artifact type

class ComponentKind(StrEnum):
    TOKENIZE_SEGMENT = "tokenize-segment"
    REVIEW_SEGMENT_TOKENIZATION = "review-segment-tokenization"
  # ... all 8 segment components from cli-spec

class UnitStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    STALE = "stale"
    BLOCKED = "blocked"
    FAILED = "failed"

class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"

class ReviewStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
```

### ADTs (Pydantic discriminated unions)

Use Pydantic models with `Field(discriminator="kind")` for in-memory results and JSON-serializable ADTs. Do not use plain `dataclass` for structured data in `wenyan_models/`.

`wenyan_models/domain/results.py`:

```python
class Skipped(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: Literal["skipped"] = "skipped"
    reason: str

class Promoted(BaseModel, Generic[T]):
    model_config = ConfigDict(frozen=True)
    kind: Literal["promoted"] = "promoted"
    artifact: T

class JobFailure(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: Literal["failure"] = "failure"
    code: str
    message: str

JobOutcome = Annotated[Promoted[T] | Skipped | JobFailure, Field(discriminator="kind")]
```

`wenyan_models/domain/spans.py` — Pydantic frozen models with `@model_validator` for span invariants:

```python
class TextSpan(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: int
    end: int

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.start < 0 or self.end < self.start:
            raise ValueError("invalid span")
        return self

class ChapterSpan(TextSpan):
    id: ChapterIdField
    title: str
```

`wenyan_models/domain/validation.py` — `CheckResult`, `SpanValidationResult` as frozen Pydantic models.

Default model config everywhere in `wenyan_models/`:

```python
model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")
```

### Port interfaces (`core/ports/`)

Protocols are the contracts jobs compile against. **Jobs never import adapters.**

`artifact_store.py`:

```python
class ArtifactStore(Protocol):
    def exists(self, ref: ArtifactRef) -> bool: ...
    def read[T: BaseModel](self, ref: ArtifactRef, model: type[T]) -> T: ...
    def write[T: BaseModel](self, ref: ArtifactRef, payload: T, *, dry_run: bool) -> None: ...
    def write_batch(self, writes: Sequence[ArtifactWrite], *, dry_run: bool) -> None: ...
    def delete(self, ref: ArtifactRef) -> None: ...
```

`ArtifactRef` is a frozen Pydantic model built through per-kind factory functions — the `ArtifactKind` determines which scope IDs are required.

`source_registry.py`:

```python
class SourceRegistry(Protocol):
    def resolve(self, id_or_slug: str) -> RegistryEntry: ...
    def assign_document_id(self, slug: Slug, document_id: DocumentId) -> None: ...
    def load_document_yaml(self, slug: Slug) -> DocumentYaml: ...
```

`llm_client.py`:

```python
class StructuredPrompt(Protocol):
    @property
    def prompt_version(self) -> PromptVersion: ...
    @property
    def template_name(self) -> str: ...
    def render(self, context: Mapping[str, str]) -> str: ...

class LLMClient(Protocol):
    def complete_model[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T: ...
```

`span_validator.py`:

```python
class SpanValidator(Protocol):
    def validate_chapters(self, text: str, chapters: Sequence[ChapterSpan]) -> SpanValidationResult: ...
    def validate_paragraphs(self, text: str, paragraphs: Sequence[ParagraphSpan]) -> SpanValidationResult: ...
    def validate_segments(self, text: str, segments: Sequence[SegmentShell]) -> SpanValidationResult: ...
```

`status_reader.py` / `graph_validator.py` — separate ports for read-heavy status and validate-artifacts so jobs stay thin.

### Application service shape (jobs)

Each job module exposes one typed entrypoint and returns `JobOutcome`, never raw `None`:

```python
def run_split_chapters(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[ChapterProposal]: ...
```

`JobContext` is a frozen `@dataclass` holding port instances (Pydantic cannot hold Protocol objects). `JobOptions` and `PreprocessingConfig` are Pydantic models.

```python
@dataclass(frozen=True)
class JobContext:
    repo_root: Path
    config: PreprocessingConfig
    artifacts: ArtifactStore
    registry: SourceRegistry
    llm: LLMClient
    spans: SpanValidator
```

### Composition root

`src/wenyan/bootstrap.py` — the only place that wires adapters to ports:

```python
def build_job_context(repo_root: Path) -> JobContext: ...
```

CLI commands call `build_job_context`, then the job function, then map `JobOutcome` → exit code.

### mypy configuration (Task 1)

Root `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_defs = true
packages = ["wenyan", "wenyan_models"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

CI/local gate per task: `uv run mypy packages/wenyan-models/src src/wenyan`

## File Map

| Path | Responsibility |
| --- | --- |
| `pyproject.toml` | uv workspace root, mypy strict config, `wenyan` console script |
| `packages/wenyan-models/src/wenyan_models/domain/` | IDs, enums, ADTs, span value objects |
| `packages/wenyan-models/src/wenyan_models/artifacts/` | preprocessing artifact Pydantic models |
| `packages/wenyan-models/src/wenyan_models/status/` | status payload Pydantic models |
| `src/wenyan/core/ports/` | `Protocol` interfaces — **no implementations** |
| `src/wenyan/core/adapters/` | port implementations (filesystem, yaml, anthropic, mock) |
| `src/wenyan/bootstrap.py` | composition root: wire adapters → `JobContext` |
| `src/wenyan/jobs/context.py` | `JobContext`, `JobOptions`, `JobOutcome` mapping |
| `src/wenyan/jobs/*.py` | application services (depend on ports only) |
| `src/wenyan/cli/preprocess.py` | Typer registration; calls bootstrap + jobs |
| `config/preprocessing.yaml` | committed defaults |
| `prompts/*.md` | versioned prompt templates |
| `tests/` | unit tests per layer; integration test at top |

---

### Task 1: Workspace scaffold and test harness

**Files:**
- Create: `pyproject.toml`, `packages/wenyan-models/pyproject.toml`, `packages/wenyan-models/src/wenyan_models/__init__.py`, `src/wenyan/__init__.py`, `src/wenyan/cli/__init__.py`, `.gitignore`, `tests/conftest.py`, `tests/test_smoke.py`
- Create: `config/preprocessing.yaml`

**Interfaces:**
- Produces: `uv run pytest` works; `uv run wenyan --help` shows root Typer app (empty preprocess group OK for now).

- [ ] **Step 1: Create root `pyproject.toml`**

```toml
[project]
name = "wenyan"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "wenyan-models",
  "typer>=0.15.0",
  "rich>=13.9.0",
  "httpx>=0.28.0",
  "pyyaml>=6.0.2",
]

[project.scripts]
wenyan = "wenyan.cli:app"

[tool.uv.sources]
wenyan-models = { workspace = true }

[tool.uv.workspace]
members = ["packages/wenyan-models"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wenyan"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[dependency-groups]
dev = ["pytest>=8.3.0", "ruff>=0.8.0", "mypy>=1.14.0"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
packages = ["wenyan", "wenyan_models"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

- [ ] **Step 2: Create `packages/wenyan-models/pyproject.toml`**

```toml
[project]
name = "wenyan-models"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.10.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wenyan_models"]
```

- [ ] **Step 3: Create minimal CLI entrypoint**

`src/wenyan/cli/__init__.py`:

```python
import typer

app = typer.Typer(no_args_is_help=True)
preprocess_app = typer.Typer(no_args_is_help=True)
app.add_typer(preprocess_app, name="preprocess")
```

- [ ] **Step 4: Create `.gitignore`**

```
.venv/
.env
.wenyan/
preprocess/
content/
__pycache__/
*.pyc
.ruff_cache/
.pytest_cache/
```

- [ ] **Step 5: Create `tests/conftest.py` workspace fixture**

```python
from pathlib import Path
import shutil
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "sources", workspace / "sources")
    (workspace / "config").mkdir()
    shutil.copy(REPO_ROOT / "config/preprocessing.yaml", workspace / "config/preprocessing.yaml")
    (workspace / "preprocess").mkdir()
    (workspace / "content").mkdir()
    return workspace
```

- [ ] **Step 6: Create smoke test**

`tests/test_smoke.py`:

```python
from typer.testing import CliRunner
from wenyan.cli import app

def test_help():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "preprocess" in result.stdout
```

- [ ] **Step 7: Create `config/preprocessing.yaml`**

```yaml
models:
  primary: claude-opus-4-8
retry:
  maxAttempts: 3
  backoffSeconds: 2
concurrency:
  default: 4
prompts:
  root: prompts
```

- [ ] **Step 8: Run verification**

```bash
uv sync
uv run mypy packages/wenyan-models/src src/wenyan
uv run pytest tests/test_smoke.py -v
uv run wenyan --help
```

Expected: mypy PASS; pytest PASS; help shows `preprocess` command group.

- [ ] **Step 9: Commit**

```bash
git init
git add pyproject.toml packages/ src/ tests/ config/ .gitignore sources/
git commit -m "chore: scaffold uv workspace and CLI entrypoint"
```

---

### Task 2: Domain models, enums, and Pydantic ADTs

**Files:**
- Create: `packages/wenyan-models/src/wenyan_models/domain/ids.py`, `enums.py`, `spans.py`, `validation.py`, `results.py`, `__init__.py`
- Test: `tests/domain/test_ids.py`, `tests/domain/test_spans.py`, `tests/domain/test_results.py`

**Interfaces:**
- Produces branded IDs (`DocumentId`, `ChapterId`, …), `ArtifactKind`, `ComponentKind`, `UnitStatus`, `ValidationStatus`, `ReviewStatus`
- Produces `TextSpan`, `ChapterSpan`, `ParagraphSpan`, `SegmentShell` with invariant checks in factories
- Produces `JobOutcome[T] = Promoted[T] | Skipped | JobFailure` ADT with exhaustive `match` helpers:

```python
def outcome_exit_code(outcome: JobOutcome[object]) -> int:
    match outcome:
        case Promoted() | Skipped(): return 0
        case JobFailure(): return 1
```

- [ ] **Step 1: Write failing span invariant test** — `ChapterSpan(start=5, end=3)` raises.

- [ ] **Step 2: Implement domain modules** per Type Architecture section.

- [ ] **Step 3: Run `uv run mypy packages/wenyan-models/src` and pytest — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add domain Pydantic models, enums, and JobOutcome ADT"
```

---

### Task 3: Port interfaces and job context

**Files:**
- Create: `src/wenyan/core/ports/artifact_store.py`, `source_registry.py`, `llm_client.py`, `span_validator.py`, `status_reader.py`, `graph_validator.py`, `__init__.py`
- Create: `src/wenyan/jobs/context.py` — `JobContext`, `JobOptions`
- Create: `src/wenyan/core/ports/artifact_ref.py` — `ArtifactRef` factories per `ArtifactKind`
- Test: `tests/core/ports/test_artifact_ref.py`

**Interfaces:**
- Produces typed `ArtifactRef` factories, e.g.:

```python
def chapter_proposal_ref(document_id: DocumentId) -> ArtifactRef: ...
def segment_tokenization_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef: ...
```

- `JobContext` — frozen `@dataclass` holding port protocols (Pydantic cannot hold Protocol instances).
- `JobOptions` — frozen Pydantic model (`force: bool`, `dry_run: bool`).

- [ ] **Step 1: Write test** — each `ArtifactKind` factory produces a distinct ref; wrong scope IDs rejected at factory.

- [ ] **Step 2: Implement port modules** — Protocols only, no filesystem/httpx imports.

- [ ] **Step 3: Run mypy — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: define port interfaces and ArtifactRef factories"
```

---

### Task 4: Filesystem `ArtifactStore` adapter

**Files:**
- Create: `src/wenyan/core/adapters/filesystem_artifact_store.py`, `src/wenyan/core/adapters/paths.py`, `src/wenyan/core/adapters/hashing.py`
- Test: `tests/core/adapters/test_filesystem_artifact_store.py`

**Interfaces:**
- Produces `FilesystemArtifactStore(repo_root: Path) -> ArtifactStore` implementing the port
- Path resolution lives in `paths.py` — maps `ArtifactRef` → `Path` (only place that knows directory layout)
- `sha256_text(text: str) -> ContentHash`
- Atomic write via temp file + `os.replace`; `write_batch` promotes as a unit

- [ ] **Step 1: Write failing round-trip test** using `ArtifactRef` + Pydantic stub model.

- [ ] **Step 2: Implement adapter**

- [ ] **Step 3: Run mypy + pytest — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add FilesystemArtifactStore adapter"
```

---

### Task 5: `PreprocessingConfig` and composition root skeleton

**Files:**
- Create: `src/wenyan/core/config/loader.py`, `src/wenyan/bootstrap.py`
- Test: `tests/core/config/test_loader.py`

**Interfaces:**
- Produces frozen `PreprocessingConfig` Pydantic model
- `PreprocessingConfig.load(repo_root: Path) -> PreprocessingConfig` merges env + YAML then `model_validate`
- `build_job_context(repo_root: Path) -> JobContext` wires `FilesystemArtifactStore`; other ports stubbed with `NotImplementedError` until later tasks

- [ ] **Step 1: Write env-overrides-YAML test**

- [ ] **Step 2: Implement loader + bootstrap skeleton**

- [ ] **Step 3: Run mypy + pytest — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add PreprocessingConfig and bootstrap skeleton"
```

---

### Task 6: `SourceRegistry` port and YAML adapter

**Files:**
- Create: `packages/wenyan-models/src/wenyan_models/sources.py` — `RegistryEntry`, `DocumentYaml` Pydantic models
- Create: `src/wenyan/core/adapters/yaml_source_registry.py`
- Test: `tests/core/adapters/test_yaml_source_registry.py`

**Interfaces:**
- Produces `YamlSourceRegistry(repo_root: Path) -> SourceRegistry`
- `resolve(id_or_slug: str) -> RegistryEntry` returns `DocumentId` + `Slug`
- `assign_document_id(slug, document_id)` updates `sources/registry.yaml`

- [ ] **Step 1: Write slug resolution test** with sunzi-bingfa fixture

- [ ] **Step 2: Implement adapter**

- [ ] **Step 3: Wire into `build_job_context`**

- [ ] **Step 4: Run mypy + pytest — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add YamlSourceRegistry adapter"
```

---

### Task 7: Pydantic artifact models, status models, and domain types

**Files:**
- Create: `packages/wenyan-models/src/wenyan_models/artifacts/` — `base.py`, `normalized.py`, `structure.py`, `paragraph.py`, `segment.py`
- Create: `packages/wenyan-models/src/wenyan_models/status/` — document/chapter/paragraph/segment status models
- Create: `packages/wenyan-models/src/wenyan_models/config.py` — `PreprocessingConfig` schema
- Extend: `domain/spans.py`, `domain/results.py`, `domain/validation.py` as Pydantic models
- Test: `tests/models/test_artifact_roundtrip.py`

**Interfaces:**
- All models use `ConfigDict(frozen=True, populate_by_name=True, extra="forbid")`
- Branded ID fields via `Annotated[..., BeforeValidator(...)]`
- Artifact models include `inputHash`, `promptVersion`, `model`, `attempts` at JSON root
- Span/domain helpers as `@model_validator` on Pydantic models — no separate mapper package unless shapes diverge

- [ ] **Step 1: Round-trip tests for `NormalizedDocument`, `ChapterProposal`, status payloads**

- [ ] **Step 2: Implement Pydantic models**

- [ ] **Step 3: Run mypy + pytest — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add Pydantic artifact, status, and domain models"
```

---

### Task 8: `SpanValidator` port and pure implementation

**Files:**
- Create: `src/wenyan/core/adapters/pure_span_validator.py`
- Test: `tests/core/adapters/test_pure_span_validator.py`

**Interfaces:**
- Produces `PureSpanValidator() -> SpanValidator`
- Returns `SpanValidationResult` Pydantic model; jobs write validation artifacts via `model_dump`
- Wire into `build_job_context`

- [ ] **Step 1: Tests** — ordered spans reconstruct text; gap/overlap/order failures

- [ ] **Step 2: Implement**

- [ ] **Step 3: Run mypy + pytest — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add PureSpanValidator adapter"
```

---

### Task 9: `LLMClient` port and adapters

**Files:**
- Create: `src/wenyan/core/adapters/anthropic_llm_client.py`, `mock_llm_client.py`, `prompt_template.py`
- Create: `prompts/*.md`, `tests/fixtures/llm/*.json`
- Test: `tests/core/adapters/test_mock_llm_client.py`

**Interfaces:**
- `PromptTemplate` frozen Pydantic model implementing `StructuredPrompt`
- `LLMClient.complete_model(prompt, model: type[T]) -> T` — parse failures raise `LLMParseError`
- `MockLLMClient(fixture_dir: Path)` keyed by `PromptVersion`
- Wire into `build_job_context`; `WENYAN_LLM_CLIENT=mock|anthropic` env switch in bootstrap

- [ ] **Step 1: Test mock returns typed `ChapterProposal`**

- [ ] **Step 2: Implement adapters + prompt templates**

- [ ] **Step 3: Run mypy + pytest — expect PASS**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add LLM port with mock and Anthropic adapters"
```

---

### Task 10: `ingest-document` application service

**Files:**
- Create: `src/wenyan/jobs/ingest_document.py`, `src/wenyan/core/adapters/normalizer.py`
- Test: `tests/jobs/test_ingest_document.py`

**Interfaces:**
- Produces:

```python
def run_ingest_document(
    ctx: JobContext,
    source_dir: Path,
    options: JobOptions,
) -> JobOutcome[DocumentId]: ...
```

- Depends on `ctx.registry`, `ctx.artifacts` only — no direct filesystem in job module
- CLI: map `JobOutcome` → exit code via `outcome_exit_code`

- [ ] **Step 1: Job test** on `tmp_workspace` with sunzi-bingfa

- [ ] **Step 2: Implement normalizer + job**

- [ ] **Step 3: Wire CLI command**

- [ ] **Step 4: Run mypy + pytest — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add ingest-document application service"
```

---

### Task 11: `split-chapters` application service

**Files:**
- Create: `src/wenyan/jobs/split_chapters.py`, `tests/fixtures/llm/chapter-structure-v1.json`
- Test: `tests/jobs/test_split_chapters.py`

**Interfaces:**

```python
def run_split_chapters(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[ChapterProposal]: ...
```

- Reads via `ctx.artifacts.read`; writes proposal + validation via `ctx.artifacts.write_batch`
- Reuse → `Skipped`; validation failure → `JobFailure` (no promotion)
- Uses `ctx.spans.validate_chapters` on `ChapterSpan` models from the chapter proposal

- [ ] **Step 1–5:** TDD job + CLI; `mypy` + pytest PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add split-chapters application service"
```

---

### Task 12: `split-paragraphs` application service

**Files:**
- Create: `src/wenyan/jobs/split_paragraphs.py`, LLM fixtures
- Test: `tests/jobs/test_split_paragraphs.py`

**Interfaces:**

```python
def run_split_paragraphs(
    ctx: JobContext,
    document_id: DocumentId,
    chapter_id: ChapterId,
    options: JobOptions,
) -> JobOutcome[ParagraphProposal]: ...
```

- [ ] **Step 1–5:** TDD job + CLI; `mypy` + pytest PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add split-paragraphs application service"
```

---

### Task 13: `split-segments` application service

**Files:**
- Create: `src/wenyan/jobs/split_segments.py`, LLM fixtures
- Test: `tests/jobs/test_split_segments.py`

**Interfaces:**

```python
def run_split_segments(
    ctx: JobContext,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
    options: JobOptions,
) -> JobOutcome[ParagraphDraft]: ...
```

- `write_batch` promotes paragraph draft + validation + all segment `input.json` atomically

- [ ] **Step 1–5:** TDD job + CLI; `mypy` + pytest PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add split-segments application service"
```

---

### Task 14: `tokenize-segment` and `review-segment-tokenization`

**Files:**
- Create: `src/wenyan/jobs/tokenize_segment.py`, `review_segment_tokenization.py`
- Test: `tests/jobs/test_tokenize_segment.py`

**Interfaces:**

```python
def run_tokenize_segment(ctx: JobContext, document_id: DocumentId, target: SegmentTarget, options: JobOptions) -> JobOutcome[TokenizationArtifact]: ...
def run_review_segment_tokenization(ctx: JobContext, document_id: DocumentId, segment_id: SegmentId, options: JobOptions) -> JobOutcome[TokenizationReviewArtifact]: ...
```

- `SegmentTarget` ADT: `SingleSegment(segment_id)` | `ParagraphBatch(paragraph_id)`
- Review rejection → `JobFailure` after writing review artifact with `ReviewStatus.REJECTED`

- [ ] **Step 1–6:** TDD approve + reject paths; `mypy` + pytest PASS

- [ ] **Step 7: Commit**

```bash
git commit -m "feat: add tokenization application services"
```

---

### Task 15: `StatusReader` port, adapter, and `status` CLI

**Files:**
- Create: `src/wenyan/core/adapters/filesystem_status_reader.py`
- Test: `tests/core/adapters/test_filesystem_status_reader.py`

**Interfaces:**
- `FilesystemStatusReader(artifacts: ArtifactStore) -> StatusReader`
- Returns typed status Pydantic models; segment `components` use `ComponentKind` enum
- Wire into `JobContext`; CLI `--json` uses `model_dump_json`

- [ ] **Step 1–5:** Golden-file test from cli-spec; `mypy` + pytest PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add StatusReader adapter and status CLI"
```

---

### Task 16: `GraphValidator` port, adapter, and `validate-artifacts` CLI

**Files:**
- Create: `src/wenyan/core/adapters/filesystem_graph_validator.py`
- Test: `tests/core/adapters/test_filesystem_graph_validator.py`

**Interfaces:**

```python
class ValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str
    message: str
    ref: ArtifactRef | None = None

class GraphValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0
```

- `FilesystemGraphValidator(artifacts: ArtifactStore) -> GraphValidator`

- [ ] **Step 1–5:** TDD stale/missing/dangling cases; `mypy` + pytest PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add GraphValidator adapter and validate-artifacts CLI"
```

---

### Task 17: Stub commands, CLI output layer, integration test

**Files:**
- Modify: `src/wenyan/cli/preprocess.py`, `options.py`, `output.py`
- Create: `tests/integration/test_sunzi_pipeline.py`

**Interfaces:**
- `CommandResult` ADT for CLI layer: `Success(output: str)` | `Failure(exit_code: int, message: str)`
- Stub commands exit 2 with stderr message
- Integration test runs full mocked pipeline; uses `build_job_context` with `MockLLMClient`

- [ ] **Step 1: Register stubs + shared options**

- [ ] **Step 2: Integration test**

- [ ] **Step 3: Final gate**

```bash
uv run ruff check .
uv run mypy packages/wenyan-models/src src/wenyan
uv run pytest -v
```

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: complete typed CLI slice with integration test"
```

---

## Spec Coverage Check

| Spec requirement | Task |
| --- | --- |
| uv workspace + strict mypy | 1 |
| Domain IDs, enums, ADTs | 2 |
| Port interfaces + `JobContext` | 3 |
| `ArtifactStore` adapter | 4 |
| `PreprocessingConfig` + bootstrap | 5 |
| `SourceRegistry` adapter | 6 |
| Pydantic artifact/status/domain models | 7 |
| `SpanValidator` adapter | 8 |
| `LLMClient` adapters | 9 |
| `ingest-document` | 10 |
| `split-chapters` | 11 |
| `split-paragraphs` | 12 |
| `split-segments` | 13 |
| `tokenize-segment` + review | 14 |
| `status` | 15 |
| `validate-artifacts` | 16 |
| Stubs + integration | 17 |
| `--force`, `--dry-run`, `--json` | 17 |
| Fail-fast `JobOutcome` | 2, 14 |

## Placeholder Scan

No TBD steps. Each task names concrete files, functions, and test commands. `mypy --strict` is a gate on every task.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-28-preprocessing-cli-slice.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
