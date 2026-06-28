# Coding Style

## Purpose

Conventions for Python code in this repo, especially the preprocessing CLI. These rules favor definitionally correct types, explicit interfaces, and thin boundaries between layers.

**Pydantic v2 is the default tool for structured data.** Use it for artifacts, config, domain value objects, discriminated unions, and YAML/JSON boundaries — not ad hoc `dict` parsing or plain dataclasses when a model fits.

## Layering

Use ports and adapters. Dependency direction is always inward toward domain types.

```text
cli/                  Typer commands, exit codes, Rich/JSON output
  ↓
jobs/                 Application services (one module per CLI command)
  ↓
core/ports/           Protocol interfaces only — no implementations
  ↓
core/adapters/        Filesystem, YAML registry, LLM providers, validators
  ↓
wenyan_models/        Pydantic models, enums, branded types
```

Rules:

- `jobs/` imports `core/ports` and `wenyan_models` only — never `core/adapters`, Typer, httpx, or direct filesystem calls.
- `core/ports/` defines `Protocol` types only — no I/O.
- `core/adapters/` implements ports; it may use filesystem, httpx, and YAML.
- `wenyan_models/` has no CLI, LLM, or filesystem imports.
- `bootstrap.py` is the sole composition root that wires adapters into `JobContext`.

## Pydantic conventions

All models in `wenyan_models/` extend `pydantic.BaseModel` unless there is a specific reason not to (see exceptions below).

Default model config:

```python
from pydantic import BaseModel, ConfigDict

class Example(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        extra="forbid",
        validate_assignment=True,
    )
```

Use this consistently:

| Use case | Pydantic feature |
| --- | --- |
| On-disk artifacts, status JSON | `BaseModel` with `Field(alias=...)` matching architecture JSON (`documentId`, etc.) |
| YAML config, registry, `document.yaml` | `model_validate()` / `model_validate_json()` on load; never manual key access |
| Branded IDs at JSON boundary | `Annotated[DocumentId, BeforeValidator(...)]` on model fields |
| Closed string sets | `StrEnum` on model fields (serializes to JSON string) |
| Command results, targets | Discriminated unions with `Field(discriminator="kind")` |
| Span invariants | `@field_validator` / `@model_validator` |
| LLM structured output | `LLMClient.complete_model(..., model: type[T]) -> T` — parse into a Pydantic model, not `dict` |
| Artifact I/O | `model_dump_json()` on write; `model_validate_json()` on read |
| Tests and golden files | `model_validate()` fixture dicts; compare with `model_dump()` |

Export JSON Schema from artifact and status models when tooling or the web app needs generated types:

```python
ChapterProposal.model_json_schema()
```

Do **not** use `json.loads` + manual dict access for structured data that has a defined shape. Parse into a model and let Pydantic raise on invalid input.

### Exceptions (non-Pydantic allowed)

- **`JobContext`** — frozen `@dataclass` holding port `Protocol` instances; Pydantic cannot validate runtime protocol objects.
- **Port `Protocol` definitions** in `core/ports/`.
- **Thin adapter internals** — local variables that never cross a boundary.

Everything else that represents data crossing a boundary should be a Pydantic model.

## Identifiers

Do not pass raw `str` for entity IDs across module boundaries. Define branded types in `wenyan_models/domain/ids.py` and validate at parse time:

```python
from typing import Annotated, NewType
from pydantic import BeforeValidator

DocumentId = NewType("DocumentId", str)

def _parse_document_id(value: object) -> DocumentId:
    if not isinstance(value, str) or not value:
        raise ValueError("document id must be a non-empty string")
    return DocumentId(value)

DocumentIdField = Annotated[DocumentId, BeforeValidator(_parse_document_id)]
```

Use `DocumentIdField` on Pydantic model fields. Use factory helpers (`document_id(value)`) at non-JSON boundaries (CLI args, test setup).

Same pattern for `ChapterId`, `ParagraphId`, `SegmentId`, `Slug`, `ContentHash`, `PromptVersion`.

## Enums

Use `enum.StrEnum` for closed sets on Pydantic models and in application code:

- `ArtifactKind` — one variant per on-disk artifact type
- `ComponentKind` — segment subjob kinds from the CLI spec
- `UnitStatus`, `ValidationStatus`, `ReviewStatus`

Do not use bare string literals for these concepts.

## ADTs and results

Use Pydantic discriminated unions — not plain dataclasses — for structured in-memory results:

```python
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

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

JobOutcome = Annotated[
    Promoted[T] | Skipped | JobFailure,
    Field(discriminator="kind"),
]
```

Same pattern for `SegmentTarget`, `SpanValidationResult`, `CheckResult`, `ValidationIssue`, `GraphValidationReport`, `ArtifactRef`.

Use exhaustive `match` on `kind` when branching. Map `JobOutcome` to exit codes in one helper (for example `outcome_exit_code`).

## Artifacts vs internal models

Organize `wenyan_models/` by concern:

| Package | Contents |
| --- | --- |
| `artifacts/` | On-disk preprocessing JSON (`ChapterProposal`, `TokenizationArtifact`, …) |
| `status/` | CLI status payloads |
| `sources/` | `registry.yaml`, `document.yaml` shapes |
| `domain/` | Spans, validation results, outcomes — still Pydantic, not dataclasses |
| `config/` | `PreprocessingConfig` schema (loaded via env + YAML merge in adapter) |

Avoid a separate mapper layer when a model can serve both roles with clear naming. Prefer explicit `to_*` / `from_*` methods on the model only when artifact JSON shape and domain shape genuinely differ.

## Port interfaces

Jobs depend on protocols, not concrete classes:

| Port | Responsibility |
| --- | --- |
| `ArtifactStore` | `read(ref, model: type[T]) -> T` and `write(ref, payload: BaseModel, ...)` |
| `SourceRegistry` | Returns Pydantic `RegistryEntry`, `DocumentYaml` |
| `LLMClient` | `complete_model(prompt, model: type[T]) -> T` |
| `SpanValidator` | Returns `SpanValidationResult` (Pydantic) |
| `StatusReader` | Returns status payload models |
| `GraphValidator` | Returns `GraphValidationReport` (Pydantic) |

`ArtifactRef` is a frozen Pydantic model built through per-kind factory functions so required scope IDs are enforced.

## Application services (`jobs/`)

Each command module exposes one typed entrypoint:

```python
def run_split_paragraphs(
    ctx: JobContext,
    document_id: DocumentId,
    chapter_id: ChapterId,
    options: JobOptions,
) -> JobOutcome[ParagraphProposal]: ...
```

- `JobContext` — frozen dataclass of port instances (see exceptions above).
- `JobOptions` — frozen Pydantic model (`force: bool`, `dry_run: bool`).
- Return `JobOutcome` — not `None`, not bare exceptions for expected failures.
- Review rejection is fail-fast: write the review artifact (`ReviewStatus.REJECTED`), return `JobFailure`, exit non-zero.

## Configuration

`PreprocessingConfig` is a Pydantic model. The loader merges env vars and YAML into a dict, then calls `PreprocessingConfig.model_validate(merged)`. Do not read config keys with string indexing in jobs or adapters.

## Static typing

- **mypy `--strict`** must pass on `packages/wenyan-models/src` and `src/wenyan` before merging.
- Pydantic models should be fully annotated; mypy pydantic plugin enabled in `pyproject.toml`:

```toml
[tool.mypy]
plugins = ["pydantic.mypy"]
```

- No untyped function definitions in production code.
- Avoid `Any`; if unavoidable, isolate behind a single adapter with a comment.
- Prefer `Protocol` over concrete inheritance for port interfaces.
- Use `TypeVar` and generic `JobOutcome[T]` / `complete_model[T]` where appropriate.

Local gate:

```bash
uv run mypy packages/wenyan-models/src src/wenyan
```

## Testing

- Construct test data with `Model.model_validate({...})` or `Model(**kwargs)` — not untyped dicts passed deep into jobs.
- Use `model_dump()` / `model_dump_json()` for golden-file comparisons.
- Unit-test ports via their adapters; test jobs with fake or mock port implementations.
- Do not call live LLM APIs in CI — use `MockLLMClient` returning validated Pydantic instances.
- Golden-file tests for status JSON against CLI spec examples.

## General principles

- **Minimize scope** — smallest correct change; no drive-by refactors.
- **Match existing patterns** — follow layer boundaries and naming in surrounding code.
- **No over-abstraction** — one-line helpers that are used once should stay inline.
- **Comments** — only for non-obvious business logic; types and models should carry most intent.

## Related docs

- [CLI Tech Stack](tech-stack/cli.md) — libraries, repo layout, tooling
- [CLI Spec](cli-spec.md) — command behavior and artifact paths
- [Intermediate Artifacts](preprocessing/intermediate-artifacts.md) — JSON shapes on disk
