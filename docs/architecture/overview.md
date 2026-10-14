# Architecture Overview

> **Architecture** — how the preprocessing CLI is built: packages, layout, dependencies, configuration. Behavior is defined in the [specs](../spec/); code conventions in [Coding Style](coding-style.md).

## Stack

| Area | Choice |
|---|---|
| Language | Python 3.12+ |
| Packaging | uv workspace; hatchling builds; console script `wenyan = "wenyan.cli:app"` |
| CLI | Typer; Rich for segment status rendering |
| Data models | Pydantic v2, in the shared `wenyan-models` package |
| HTTP / LLM | httpx (sync) against the Anthropic Messages API |
| Config | PyYAML + hand-rolled `.env` loader |
| Quality gate | Ruff (lint), mypy `--strict` with the Pydantic plugin, pytest — all run in CI (`.github/workflows/ci.yml`) |

There is no async code or worker pool yet ([Job execution proposal](../proposals/job-execution.md)). The reader web app is not started ([Web App](webapp.md)).

Out of scope for the CLI stage: a reader UI or dev server, publishing to PyPI, and an embedded database or search index.

## Packages

| Package | Path | Depends on | Role |
|---|---|---|---|
| `wenyan-models` | `packages/wenyan-models/src/wenyan_models/` | pydantic only | Source of truth for artifact, reader package, status, and config shapes. Safe to import from any runtime, including a future web app. |
| `wenyan` | `src/wenyan/` | `wenyan-models`, typer, rich, httpx, pyyaml | Preprocessing CLI. |

## Layout

```text
config/preprocessing.yaml   committed defaults (models, retry, concurrency, prompts root)
prompts/                    one Markdown template per LLM task
sources/                    source texts + registry.yaml
preprocess/                 committed intermediate artifacts
content/                    committed reader packages
.opencode/skills/           agent skills for interactive steps

packages/wenyan-models/src/wenyan_models/
  artifacts/    preprocessing artifact models; DEFAULT_ARTIFACT_CONFIG; *IdField aliases
  reader/       reader package models
  status/       status payloads per scope
  show/         SegmentShowView (segment status)
  domain/       ids, enums, JobOutcome, spans, targets, validation, review findings
  text/         tokenization text helpers
  config.py     PreprocessingConfig
  sources.py    RegistryEntry, DocumentYaml

src/wenyan/
  bootstrap.py  composition root: build_job_context()
  cli/          Typer app (preprocess.py), option/scope parsing, unit refs, Rich output
  jobs/         one module per command; segment_runner; JobContext/JobOptions
  core/
    ports/      Protocol interfaces + ArtifactRef factories
    adapters/   filesystem store/status/validator, YAML registry, LLM clients, hashing, paths
    config/     config loader
    assembly/   paragraph compile, validation, input hash
    package/    document package build, validate, promote
    gloss/      candidate filtering, glossary draft merge, reuse normalization
    notes/      note normalization
    run/        segment pipeline order, work queue, orphan/stale pruning
    status/     status derivation
    show/       segment view builder

tests/          mirrors src/ (cli, core, jobs, models, prompts, integration); fixtures/llm holds mock responses
```

## Request flow

```text
cli/preprocess.py ─ parse args, resolve unit refs (cli/unit_refs, cli/status_scope)
  → bootstrap.build_job_context()  ─ load config, wire adapters into JobContext
  → jobs/<command>.run_*(ctx, ids, options) → JobOutcome
  → cli prints outcome / JSON, maps to exit code
```

`status` and `validate-artifacts` construct their adapters directly in `cli/preprocess.py` rather than through `JobContext`.

## Configuration

`core/config/loader.py` builds a `PreprocessingConfig`. Precedence, highest first:

1. Shell environment
2. `<repo>/.env` (gitignored; applied with `setdefault`, so the shell wins)
3. `WENYAN_CONFIG` file, else `<repo>/.wenyan/config.yaml` (gitignored)
4. `config/preprocessing.yaml`
5. Model defaults (`provider: mock`)

Environment variables read: `WENYAN_MODEL_PROVIDER` (`mock` | `anthropic` | `minimax`), `WENYAN_MODEL` (model id for the active provider), `ANTHROPIC_API_KEY`, `MINIMAX_API_KEY`, `WENYAN_CONFIG`.

`config.concurrency` is loaded but unused; see the [Job execution proposal](../proposals/job-execution.md#concurrency-and-rate-limits).

## Cross-cutting conventions

| Concern | Convention |
|---|---|
| Ids | Document ids are code-minted UUID v4. Chapter ids come from the editor; paragraph, segment, token, note, and gloss ids come from the model. |
| Hashing | SHA-256, `sha256:` prefix (`core/adapters/hashing.py`). |
| JSON | camelCase aliases on disk; models reject unknown fields. |
| Status | Derived from files on disk; no status store. |

## Open questions

- How should the web app consume `wenyan-models`: exported JSON Schema, generated TypeScript, or both? (Backlog H9.)
- Introduce SQLite for indexing, or defer until search is needed?
