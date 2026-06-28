# CLI Tech Stack

## Purpose

Define libraries, project structure, and implementation patterns for the preprocessing CLI.

Command behavior, flags, scopes, and output shapes are defined in the [CLI Spec](../cli-spec.md). This doc does not repeat them. When implementation choices matter for a particular command, note them here and link to the spec.

## Decision Summary

| Area | Choice |
| --- | --- |
| Language | Python 3.12+ |
| CLI framework | [Typer](https://typer.tiangolo.com/) |
| Terminal output | [Rich](https://rich.readthedocs.io/) |
| Package layout | `pyproject.toml` with a `wenyan` console script |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Data validation | Pydantic v2 |
| HTTP / LLM calls | httpx (sync and async) |
| Concurrency | `asyncio` with a bounded worker pool |
| Tests | pytest |
| Lint and format | Ruff |

## Why Python

Preprocessing is file-heavy, text-heavy, and LLM-heavy. Python fits artifact graph traversal, validation, prompt assembly, and resumable job orchestration without coupling those concerns to the reader UI.

## Shared Models

Content shapes — reader package files, preprocessing artifacts, and CLI status payloads — should live in reusable Pydantic models that both the CLI and web app can depend on.

Design the models as a shared library from the start, even if the first implementation keeps them in-repo beside the CLI:

- Pydantic models are the source of truth for field names, types, and validation rules.
- Parse all JSON/YAML artifacts and config through `model_validate` / `model_validate_json`; do not use ad hoc `dict` access.
- Export JSON Schema from models when the web app or other tooling needs generated types.

Keep CLI-only concerns (Typer wiring, Rich output, job orchestration) separate from model definitions so the shared library stays lightweight and portable.

## Why Typer

Typer sits on Click and fits a large, nested command tree:

- Nested command groups map cleanly to the spec's top-level structure.
- Type hints validate arguments and options at parse time.
- Docstrings become user-facing `--help` text with minimal boilerplate.
- Typer integrates cleanly with Rich for readable default output and machine-readable output when the spec calls for it.

Alternative considered: plain Click. Click is mature, but Typer reduces repetition when many commands share similar arguments and options.

## Distribution

Install the CLI as an editable local package:

```shell
uv sync
uv run wenyan --help
```

`pyproject.toml` declares a console script:

```toml
[project.scripts]
wenyan = "wenyan.cli:app"
```

Editors invoke `wenyan` directly once the environment is synced. CI and docs should use the same entry point.

## Repository Layout

Keep CLI wiring separate from preprocessing logic so commands stay thin and testable. Keep shared models separate from both so the CLI and web app can depend on them without pulling in CLI or UI code:

```text
packages/
  wenyan-models/         # shared Pydantic models; no CLI or UI imports
    src/wenyan_models/
      reader/            # document.json, chapter, paragraph, gloss shapes
      artifacts/         # preprocessing artifact shapes
      status/            # status payload shapes
src/wenyan/
  cli/
    __init__.py          # Typer root app
    preprocess.py        # preprocess command group registration
    options.py           # shared flags from the CLI spec
    output.py            # human tables vs JSON emitters
  core/
    artifacts/           # paths, atomic writes, input-hash helpers
    status/              # effective status from artifact graph on disk
    validate/            # schema and graph integrity checks
    run/                 # dependency-ordered chained execution
  jobs/                  # one module per artifact-producing command
  llm/                   # provider clients, prompt loading, retry policy
tests/
```

Principles:

- `wenyan-models` holds Pydantic models only. Both the CLI and web app depend on it.
- `cli/` parses arguments, selects output mode, maps exit codes, and delegates.
- `core/` holds deterministic logic with no Typer imports.
- `jobs/` implements artifact-producing commands defined in the CLI spec.

## CLI Wiring

Register commands to match the [CLI Spec](../cli-spec.md). Each command module exports a Typer callback.

Implementation patterns:

- Put flags and options defined in the spec in `cli/options.py` and attach them through Typer context or reusable decorators so they stay consistent across commands.
- Use `cli/output.py` to switch between Rich layout and serialized output. When the spec requires machine-readable output, serialize Pydantic models to stdout and keep progress or diagnostic detail on stderr so shell piping stays predictable.
- Map spec-defined exit semantics in one place rather than per command.

## Artifact Writes

All artifact-producing commands share a helper in `core/artifacts/`:

1. Write to a temporary path beside the final artifact.
2. Validate content against the Pydantic model for that artifact type.
3. Rename into the final path only after all required outputs for that component are ready.

This implements the atomic-write requirement from the CLI spec and preprocessing docs. Failed LLM calls or parser errors must not leave a final artifact that status could treat as complete.

## Validation And Status

Pydantic models in `wenyan-models` represent artifact types, status payloads, and reader package files. The CLI imports them for validation, serialization, and machine-readable output.

- `core/status/` derives effective status from files on disk. Behavior follows the CLI spec and [Intermediate Artifacts](../preprocessing/intermediate-artifacts.md).
- `core/validate/` implements graph-integrity checks: schema match, input-hash match, referential integrity, and stale downstream detection.

Do not maintain a separate status database. The artifact graph on disk is the source of truth.

## Configuration

All runtime settings flow through a centralized `PreprocessingConfig` in `core/config/`. Jobs, the LLM adapter, and CLI commands read from this loader — they do not read environment variables or YAML files directly.

Resolution order (highest precedence first):

1. Environment variables (`MINIMAX_API_KEY`, `ANTHROPIC_API_KEY`, `WENYAN_MODEL_PROVIDER`, `WENYAN_MODEL`, `WENYAN_CONFIG`, …)
2. Local override file (`.wenyan/config.yaml` or the path from `WENYAN_CONFIG`)
3. Repo defaults (`config/preprocessing.yaml`)

Secrets belong in environment variables or a gitignored local override. Committed YAML holds models, retry limits, concurrency defaults, and prompt root paths only.

## Job Execution

Artifact-producing commands delegate to `jobs/` modules. Job modules call into shared helpers for input hashes, prompt versions, artifact reuse, and job metadata recording. Behavioral rules come from the CLI spec and [Job Execution](../preprocessing/job-execution.md).

Chained multi-command execution lives in `core/run/`. LLM-facing work lives in `llm/` and uses httpx with explicit timeouts and retry policy. Model choice and prompt versioning are covered in [Model Strategy](../preprocessing/model-strategy.md).

## Testing

Use pytest with a temporary workspace fixture:

- Build minimal artifact trees on disk and assert effective status results.
- Test atomic write behavior and stale detection after upstream deletion.
- Test CLI parsing and exit codes through Typer's `CliRunner`.
- Keep LLM calls behind interfaces so job tests use fixtures instead of live API calls.

Golden-file tests are useful for machine-readable status payloads. Use the examples in the CLI spec as fixtures.

## Development Tooling

| Tool | Role |
| --- | --- |
| uv | Dependency lockfile, virtualenv, and script runner |
| Ruff | Lint and format |
| pytest | Unit and CLI integration tests |
| mypy | Optional static typing on `core/` and `wenyan-models` |

Local development assumes macOS or Linux with Python 3.12+. No container requirement for the first stage.

## Non-Goals For The First CLI Stage

- Reader web UI or local dev server.
- Published package distribution to PyPI.
- Embedded database or search index.

## Related Docs

- [CLI Spec](../cli-spec.md)
- [Preprocessing](../preprocessing/README.md)
- [Intermediate Artifacts](../preprocessing/intermediate-artifacts.md)
- [Editor Workflow](../preprocessing/editor-workflow.md)
- [Storage Format](../storage-format.md)
