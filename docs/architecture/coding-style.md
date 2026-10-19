# Coding Style

> **Architecture** — rules for Python code in this repo. New code follows them; known deviations are listed at the end. Layout and stack: [Overview](overview.md).

Favor precise types, explicit interfaces, and thin layer boundaries. **Pydantic v2 is the default for structured data.**

## Layering

Ports and adapters; dependencies point inward.

```text
cli/            Typer commands, output, exit codes
  ↓
jobs/           application services, one module per command
  ↓
core/<logic>/   deterministic logic (assembly, package, gloss, notes, run, status, show)
core/ports/     Protocol interfaces
  ↓
core/adapters/  filesystem, YAML, LLM providers
  ↓
wenyan_models/  Pydantic models, enums, branded ids
```

- `jobs/` imports ports, `core/` logic modules, and `wenyan_models` — never `core/adapters`, Typer, httpx, or the filesystem directly.
- `core/ports/` holds `Protocol`s and small frozen value types (`ArtifactRef`, `ArtifactWrite`) — no I/O.
- Non-adapter `core/` modules do no I/O and do not import adapters; they receive ports.
- `core/adapters/` implements ports and may use the filesystem, httpx, and YAML.
- `wenyan_models/` imports only pydantic and the standard library.
- `bootstrap.py` is the only composition root.

## Pydantic

Default config for artifact, reader, status, and domain models is `DEFAULT_ARTIFACT_CONFIG` in `wenyan_models/base.py`:

```python
ConfigDict(frozen=True, populate_by_name=True, validate_by_name=True, extra="forbid")
```

| Use case | Pattern |
|---|---|
| On-disk JSON | `Field(alias="camelCase")`; `model_dump_json(by_alias=True)` to write, `model_validate_json` to read |
| YAML / config | load, merge dicts, then `model_validate` once; no string-key access in jobs |
| Ids on fields | `*IdField` aliases (`Annotated[DocumentId, BeforeValidator(...)]`) |
| Closed sets | `StrEnum` |
| LLM output | `LLMClient.complete_model(prompt, Model) -> Model` |
| Invariants | `@field_validator` / `@model_validator` |

Never `json.loads` + dict access for data with a defined shape.

Non-Pydantic is allowed for: `JobContext` (holds Protocol instances), Protocol definitions, port value types, and adapter-internal values that never cross a boundary.

## Ids

Do not pass raw `str` ids across modules. Branded `NewType`s live in `wenyan_models/domain/ids.py` (`DocumentId`, `ChapterId`, `ParagraphId`, `SegmentId`, `Slug`, `ContentHash`), with factory helpers (`document_id(value)`) for CLI args and tests.

## Enums

Use `StrEnum` for `ComponentKind`, `UnitStatus`, `ValidationStatus`, `ReviewStatus` (`wenyan_models/domain/enums.py`). No bare string literals for these.

## Results

Jobs return `JobOutcome[T]` (`wenyan_models/domain/results.py`):

```python
type JobOutcome[T] = Promoted[T] | Skipped | JobFailure
```

Each variant has a `kind` literal. Branch with exhaustive `match`; map to exit codes only via `outcome_exit_code`. Return `JobFailure` for expected failures instead of raising. Review rejection writes the review, then returns `JobFailure`.

## Ports

| Port | Responsibility |
|---|---|
| `ArtifactStore` | `read`, `write`, `write_batch`, `exists`, `delete` by `ArtifactRef` |
| `NormalizedTextStore` | normalized text sidecar and manifest |
| `SourceRegistry` | `RegistryEntry`, `DocumentYaml` |
| `LLMClient` | `complete_model` |
| `PromptLoader` | `build_prompt(template_name, context)` |
| `StatusReader` | status payloads |
| `GraphValidator` | validation report |

## Typing

- `mypy --strict` with the Pydantic plugin passes on `packages/wenyan-models/src` and `src/wenyan` (enforced in CI).
- No untyped defs. Avoid `Any`; isolate it behind one adapter if unavoidable.
- Use PEP 695 generics (`def f[T: BaseModel](...)`, `type Alias[T] = ...`).
- Name repeated or long `Callable` signatures as `type` aliases.

## Testing

- Always run via `uv run python -m pytest` ([AGENTS.md](../../AGENTS.md#running-tests)).
- Build test data with `Model(...)` or `Model.model_validate({...})`.
- Test jobs with `build_job_context(tmp_workspace)` and `MockLLMClient`; never call a live LLM.
- Test CLI parsing and exit codes with `CliRunner`.

## General

- Smallest correct change; no drive-by refactors.
- Match surrounding patterns and naming.
- Inline one-use helpers.
- Comment only non-obvious logic.

## Known deviations

Tracked in the [backlog](../backlog.md) (H6, H8):

- `core/run` imports `core.adapters.paths`; `core/run/stale_assembly.py`, `core/run/orphan_segments.py`, and `core/package/promote.py` touch the filesystem directly.
- `cli/preprocess.py` constructs `FilesystemStatusReader` and `FilesystemGraphValidator` outside `bootstrap.py`.
- `core/status/derivation.py` builds payloads from hand-written camelCase dicts.
- Several internal frozen dataclasses (assembly inputs, package collection, status rows) and `json.loads` use in `MockLLMClient`.
