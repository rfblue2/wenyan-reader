# AGENTS.md

Wenyan Reader is a local Classical Chinese reader. A preprocessing CLI (`uv run wenyan preprocess …`) turns full source texts into reader packages under `content/`. LLMs are used only during preprocessing, never at read time. Overview: [README](README.md).

## Where to look

| Need | Start at |
|---|---|
| What to work on next | [Backlog](docs/backlog.md) — reconcile with `status`, tests, and recent commits |
| Any design question | [Docs index](docs/index.md) |
| Vocabulary | [Glossary](docs/glossary.md) |
| CLI behavior | [CLI](docs/spec/cli.md) |
| Artifact shapes, status rules | [Artifacts](docs/spec/artifacts.md) |
| Code structure and rules | [Architecture overview](docs/architecture/overview.md), [Coding Style](docs/architecture/coding-style.md) |

## Skills

| Task | Skill |
|---|---|
| Normalize a source and agree chapter boundaries | [preparing-source-structure](.opencode/skills/preparing-source-structure/SKILL.md) |
| Run and resume segment preprocessing | [preprocessing-segments](.opencode/skills/preprocessing-segments/SKILL.md) |
| Draft segment context notes | [drafting-context-notes](.opencode/skills/drafting-context-notes/SKILL.md) |
| Review segment context notes | [reviewing-context-notes](.opencode/skills/reviewing-context-notes/SKILL.md) |

Editors address segments by slug plus ordinals, e.g. "sunzi-bingfa ch1 p1 seg1" (same as `status --chapter 1 --paragraph 1 --segment 1`). The context CLI commands are stubs; use the skills.

## Rules

- Docs describe current behavior. When you change behavior, update the matching spec in the same change; put unbuilt intent in the backlog or `docs/proposals/`. Conventions: [Docs index](docs/index.md#conventions).
- Use terms from the [glossary](docs/glossary.md).
- Follow [Coding Style](docs/architecture/coding-style.md).

## Before committing

Run the full gate and fix failures. Same as [CI](.github/workflows/ci.yml):

```bash
uv run ruff check packages/wenyan-models/src src/wenyan tests
uv run mypy packages/wenyan-models/src src/wenyan
uv run python -m pytest
```

## Running Tests

Always use uv, never bare `python`/`python3`. On some machines `python` is a broken pyenv shim that hangs or fails before collecting tests.

```bash
uv run python -m pytest
uv run python -m pytest tests/jobs/test_gloss_segment.py -q
```

- Tests use `build_job_context(tmp_workspace)` with the mock provider and fixtures in `tests/fixtures/llm/`; `tmp_workspace` clears provider env vars so `.env` does not leak in.
- A healthy suite finishes in seconds. If it seems stuck, rerun with a 60–120 s timeout or a narrow path; do not poll.

More: [Jobs and LLM — Testing](docs/architecture/jobs-and-llm.md#testing).
