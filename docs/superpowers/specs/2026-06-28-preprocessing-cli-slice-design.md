# Preprocessing CLI Vertical Slice Design

## Summary

Implement a thin vertical slice of the preprocessing CLI: real LLM-backed commands from ingest through segment tokenization review, plus status and validate infrastructure. All other CLI commands are registered but stubbed.

## Decisions

| Topic | Decision |
| --- | --- |
| Scope | Thin vertical slice with real LLM |
| Package layout | `packages/wenyan-models/` + `src/wenyan/` per CLI tech stack |
| Source layout | `sources/documents/<slug>/` with `source.txt` + `document.yaml` |
| Registry | `sources/registry.yaml` — document-level fields only (slug, title, status, documentId) |
| CLI id resolution | Accept UUID or slug (resolved via registry) |
| Ingest input | Directory only |
| Workspace roots | `preprocess/documents/<id>/` for artifacts; `content/documents/<id>/` for reader package |
| Validation reports | Sibling `*.validation.json` files |
| Job metadata | Embedded in output artifact headers |
| Segment assembly | `assemble-paragraph` reads accepted subjob outputs directly |
| Config | Centralized `PreprocessingConfig`: env vars → `.wenyan/config.yaml` → `config/preprocessing.yaml` |
| LLM (slice) | Anthropic only, behind `LLMClient` protocol |
| Review failure | Fail-fast — non-zero exit, write review report, editor reruns manually |
| Test document | `sources/documents/sunzi-bingfa/` (孙子兵法) |

## Package Layout

```text
packages/wenyan-models/src/wenyan_models/
  artifacts/
  status/
  reader/

src/wenyan/
  cli/
  core/
    config/
    artifacts/
    status/
    validate/
  jobs/
  llm/

config/preprocessing.yaml
prompts/
sources/
preprocess/
content/
```

**Boundaries:** `cli/` parses and delegates; `core/` has no Typer imports; `jobs/` calls `core/` + `llm/`; `wenyan-models` has no CLI or LLM imports.

## Source And Registry

```text
sources/
  registry.yaml
  documents/
    sunzi-bingfa/
      source.txt
      document.yaml
```

`registry.yaml` lists documents at the top level only — no chapter, paragraph, or segment trees.

`ingest-document sources/documents/sunzi-bingfa` assigns a UUID, updates the registry, and writes `preprocess/documents/<documentId>/normalized-document.json`.

## Artifacts (slice)

```text
preprocess/documents/<documentId>/
  normalized-document.json
  structure/
    chapter-proposal.json
    chapter-proposal.validation.json
    chapters/<chapterId>/
      paragraph-proposal.json
      paragraph-proposal.validation.json
      summary.json
  jobs/
    paragraphs/<paragraphId>/
      draft.json
      validation.json
    segments/<segmentId>/
      input.json
      tokenization.json
      tokenization-review.json
      raw-llm/
```

## Slice Commands

### Implemented (real LLM)

| Command | Slice scope |
| --- | --- |
| `ingest-document` | `sources/documents/sunzi-bingfa` |
| `split-chapters` | full document |
| `split-paragraphs` | chapter 1 (`始計第一`) |
| `split-segments` | first paragraph |
| `tokenize-segment` | first segment |
| `review-segment-tokenization` | first segment |
| `status` | all scopes that exist |
| `validate-artifacts` | all scopes that exist |

### Stubbed

All other commands from the CLI spec register in Typer and exit with a clear not-implemented message.

### Flags

`--force`, `--dry-run`, `--json` on implemented commands.

### Failure behavior

- Deterministic validation failure: non-zero exit, no final artifact promoted
- LLM parse failure: non-zero exit, optional `raw-llm/` diagnostic, no final artifact
- Review rejection: non-zero exit, write review artifact with `status: rejected` and findings, component shows as `blocked` in status

## Configuration

`PreprocessingConfig` in `core/config/` resolves settings in order:

1. Environment variables (`ANTHROPIC_API_KEY`, `WENYAN_MODEL_PRIMARY`, `WENYAN_CONFIG`, …)
2. Local override file (`.wenyan/config.yaml` or path from `WENYAN_CONFIG`)
3. Repo defaults (`config/preprocessing.yaml`)

Secrets never appear in committed YAML. Local `.env` supported via uv for development.

## Testing

- pytest with temporary workspace fixture
- Golden-file tests for status payloads (cli-spec examples)
- LLM calls mocked via `LLMClient` interface in unit tests
- Integration test path: sunzi-bingfa ingest → chapter 1 → first paragraph → first segment tokenization (mocked LLM in CI; live LLM optional locally)

## Follow-up (after slice)

- `review-paragraph-structure`, gloss, grammar, context subjobs and reviews
- `assemble-paragraph`, `package-document`, `run`
- `show`, `review-report`
- Document indexes and glossary aggregation
- Gemini long-context routing
