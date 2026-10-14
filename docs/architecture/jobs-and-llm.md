# Jobs and LLM

> **Architecture** — how jobs execute and call models. Behavior contracts: [CLI](../spec/cli.md), [Artifacts](../spec/artifacts.md). Proposed changes: [LLM output correctness](../proposals/llm-output-correctness.md), [backlog](../backlog.md).

## Job shape

Each command has a module in `src/wenyan/jobs/` with one entrypoint:

```python
def run_<command>(ctx: JobContext, <ids>, options: JobOptions) -> JobOutcome[T]
```

- `JobContext` (frozen dataclass): `repo_root`, `config`, and ports — `artifacts`, `normalized_text`, `registry`, `llm`, `spans`, `hasher`, `prompts`. Built by `bootstrap.build_job_context()`.
- `JobOptions`: `force`, `dry_run`.
- `JobOutcome[T] = Promoted[T] | Skipped | JobFailure`. Expected failures are returned, not raised.

## Segment jobs

The six LLM segment jobs share `jobs/segment_runner.py`. A job is a spec plus a `prepare` function:

| Spec | Fields |
|---|---|
| `SegmentAnnotateJobSpec` | prompt name, output model, artifact ref, component kind, optional `post_process` (punctuation drop, gloss dedup, note normalization) |
| `SegmentReviewJobSpec` | prompt name, output model, review ref, reject message, optional `post_write` (glossary merge) |

Runner steps:

1. `prepare` loads upstream artifacts, checks prerequisites (`blocked-upstream`), and returns `(input_hash, prompt_context)`.
2. `skip_if_current`: return `Skipped` if the existing artifact has the same `inputHash` and not `--force`.
3. Render the prompt and call `ctx.llm.complete_model(prompt, OutputModel)`.
4. Post-process; stamp `segmentId`, `inputHash`, `model`, `attempts=1` (overwriting model-echoed values).
5. Unless `--dry-run`: annotate jobs delete the paired review, then write. Review jobs write, then return `JobFailure("review-rejected")` if rejected, else run `post_write`.

`run_segment_batch` resolves `--paragraph` to the draft's segment ids and runs them in order, stopping at the first failure.

`jobs/run_preprocess.py` chains components using the fixed order in `core/run/segment_pipeline.py` and the work queue in `core/run/work_queue.py`.

## Writes

`FilesystemArtifactStore` resolves an `ArtifactRef` to a path (`core/adapters/paths.py`), writes `<name>.tmp`, and `os.replace`s it. `write_batch` writes all temps before renaming. `ArtifactRef` factories in `core/ports/artifact_ref.py` enforce required scope ids per artifact kind.

## Prompts

Templates live in `prompts/<name>.md` with `{{placeholder}}` slots filled from the prepare context (JSON-serialized artifacts, segment text, ids, input hash). `PromptLoader` renders them into a `StructuredPrompt`.

## LLM clients

| Provider | Client | Endpoint | Default model (`config/preprocessing.yaml`) |
|---|---|---|---|
| `mock` (default) | `MockLLMClient` | fixtures in `tests/fixtures/llm/`, dispatched by template name | — |
| `anthropic` | `AnthropicLLMClient` | `https://api.anthropic.com/v1/messages` | `claude-opus-4-8` |
| `minimax` | `MiniMaxLLMClient` (subclass) | `https://api.minimax.io/anthropic` | `MiniMax-M2.5-highspeed` |

One provider and model serve every job. `.env.example` suggests MiniMax for development and Anthropic for higher-quality runs.

Request: raw httpx, `max_tokens: 8192`, timeout 120 s (connect 30 s), no temperature.

### Structured output

Prompt-only:

1. `build_structured_system_prompt` embeds the output model's JSON Schema and asks for one JSON object.
2. `extract_json_text` strips code fences or slices from the first `{` to the last `}`.
3. `parse_model_json` validates with Pydantic (`extra="forbid"`); failure raises `LLMParseError`.

No provider JSON mode or tool use.

### Retries

Up to `retry.maxAttempts` (3) with linear backoff (`backoffSeconds × attempt`: 2 s, 4 s) on HTTP 429/5xx, transport errors, and `LLMParseError` (same prompt re-sent). Other 4xx raise immediately. Jobs do not catch final errors, so the CLI exits with a traceback.

## Testing

- `tmp_workspace` (in `tests/conftest.py`) copies `sources/`, `prompts/`, `tests/fixtures/`, and config into a temp repo, forces `provider: mock`, and clears provider env vars.
- `build_job_context(tmp_workspace)` gives jobs a real filesystem store and the mock client.
- CLI tests use Typer's `CliRunner`. No test calls a live LLM.
