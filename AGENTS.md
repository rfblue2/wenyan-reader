# AGENTS.md

## Project Context

This repo is designing a local Classical Chinese reader. The app should consume curated local content files; LLMs are used only during preprocessing, never at reader runtime.

When the editor asks what is left to do or what to work on next, start from [Project backlog](docs/backlog.md) and reconcile with the current tree (status commands, tests, and recent changes).

Most project details live in the architecture docs. Start there before making design changes, especially the docs covering:

- Final reader content shape.
- Preprocessing overview and pipeline stages.
- Preprocessing CLI commands and status behavior.
- Editor-facing user flows.
- Resumable artifact layout and effective status rules.
- Job graph, resumability, and failure behavior.
- Validation and review passes.

## Vocabulary

- `document`: the canonical source and content unit.
- `chapter`: a top-level structural division within a document.
- `paragraph`: a structural unit used for context framing and segment boundary discovery.
- `segment`: unit of text shown to reader and also smallest unit of text to preprocess
- `artifact`: an intermediate preprocessing file used for auditability, validation, reruns, and packaging.

## Preprocessing Principles

- Preserve intermediate artifacts for auditability and reruns.
- Derive effective status from the artifact graph on disk, not only from manifest metadata.
- Missing artifacts are pending; downstream artifacts with missing or changed inputs are stale.
- Artifact-producing commands should write temporary files first and atomically promote final artifacts only after validation.
- The reader package should depend only on validated final files.

## Editing Guidance

- Follow [Coding Style](docs/architecture/coding-style.md) for Python layer boundaries, Pydantic usage, ports, and static typing.
- For interactive source normalization and chapter boundaries, use the [preparing-source-structure](.opencode/skills/preparing-source-structure/SKILL.md) skill.
- For segment-local **context notes** (draft or review), use [drafting-context-notes](.opencode/skills/drafting-context-notes/SKILL.md) and [reviewing-context-notes](.opencode/skills/reviewing-context-notes/SKILL.md). The editor only needs document slug + chapter/paragraph/segment ordinals (same as `preprocess status --segment`); context annotate/review CLI commands are stubbed.
- Keep architecture docs concise and cross-link rather than duplicating large sections.
- When changing CLI behavior, update the CLI spec and any affected workflow examples.
- When changing artifact shapes or status semantics, update the artifact documentation.
- After doc edits, check terminology against the vocabulary above.

## Before committing

When the editor asks for a commit, run the full local gate first and fix anything that fails:

```bash
uv run ruff check packages/wenyan-models/src src/wenyan tests
uv run mypy packages/wenyan-models/src src/wenyan
uv run python -m pytest
```

Do not commit until all three pass. This matches [CI](.github/workflows/ci.yml).

## Running Tests

Always invoke pytest through **uv** — do not use bare `python` or `python3`:

```bash
uv run python -m pytest
uv run python -m pytest tests/jobs/test_gloss_segment.py -q
```

- **Why uv:** On some machines, `python` resolves to a broken pyenv shim (for example a missing `libintl.8.dylib`) and pytest may hang or fail before collecting tests.
- **No live LLM:** Job and pipeline tests use `build_job_context(tmp_workspace)` with `models.provider: mock` and `MockLLMClient` fixtures under `tests/fixtures/llm/`. The `tmp_workspace` fixture clears `WENYAN_MODEL_PROVIDER`, `WENYAN_MODEL`, and API key env vars so a developer `.env` does not leak in.
- **Bounded waits:** If a test run seems stuck, do not poll indefinitely. Re-run with a subprocess timeout (60–120s) or a narrow path to tell a hung interpreter from a slow test. A healthy full suite finishes in seconds.

See also [Jobs and LLM — Testing](docs/architecture/jobs-and-llm.md#testing).
