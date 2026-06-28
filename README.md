# Wenyan Reader

A local Classical Chinese reader built from curated content files. Editors preprocess full source texts into structured, validated packages; the reader app loads those files only—no live LLM calls at read time.

Preprocessing is incremental and resumable: each stage writes inspectable artifacts under `preprocess/documents/<document-id>/`, so you can review boundaries, rerun small units, and validate the artifact graph before packaging.

The reader app reads from `content/documents/<document-id>/` — validated packages (`document.json`, chapters, paragraphs, glosses). Both `preprocess/` and `content/` are tracked in git so clones and CI have real data without rerunning the pipeline.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12+)

From the repository root:

```shell
uv sync
```

By default the CLI uses the **mock** model provider (deterministic, no API key). For live model calls, set `models.provider` in config or use environment variables:

**MiniMax** (cost-effective for development):

```shell
export WENYAN_MODEL_PROVIDER=minimax
export MINIMAX_API_KEY=...
```

**Anthropic** (higher-quality preprocessing):

```shell
export WENYAN_MODEL_PROVIDER=anthropic
export ANTHROPIC_API_KEY=...
```

Each provider has a default model in `config/preprocessing.yaml` (`anthropic.model`, `minimax.model`). Override with `WENYAN_MODEL` only when you need a different model ID for the active provider.

Copy [`.env.example`](.env.example) to `.env` in the repo root and fill in your keys there — `.env` is gitignored and `uv run` loads it automatically. Never commit API keys.

## Quickstart: preprocess 孙子兵法

The repo includes [孙子兵法](sources/documents/sunzi-bingfa/) (`sunzi-bingfa`) as a worked example. Run commands from the repo root.

### 1. Ingest and normalize

```shell
uv run wenyan preprocess ingest-document sources/documents/sunzi-bingfa
```

This assigns a document UUID, updates `sources/registry.yaml`, and writes `preprocess/documents/<document-id>/normalized-document.json` and `normalized-text.txt`.

### 2. Define chapter structure (interactive)

Work with a local agent using the [preparing-source-structure](.cursor/skills/preparing-source-structure/SKILL.md) skill to normalize and agree on chapter boundaries. The agent writes `preprocess/documents/<document-id>/structure/chapter-proposal.json`.

```shell
uv run wenyan preprocess validate-artifacts sunzi-bingfa
uv run wenyan preprocess status sunzi-bingfa --json
```

Commands accept either the UUID or the slug (`sunzi-bingfa`). Use `status --json` to list chapter IDs and titles.

Pick a chapter (below, the first chapter from status):

```shell
CHAPTER_ID=<chapter-id-from-status>
uv run wenyan preprocess split-paragraphs sunzi-bingfa --chapter "$CHAPTER_ID"
```

Paragraph IDs live in the chapter’s `paragraph-proposal.json` artifact:

```shell
PARAGRAPH_ID=$(python3 -c "
import json, glob
path = glob.glob('preprocess/documents/*/structure/chapters/' + '$CHAPTER_ID' + '/paragraph-proposal.json')[0]
print(json.load(open(path))['paragraphs'][0]['id'])
")
```

### 3. Segment one paragraph

```shell
uv run wenyan preprocess split-segments sunzi-bingfa --paragraph "$PARAGRAPH_ID"
```

Segment IDs are in the paragraph draft:

```shell
SEGMENT_ID=$(python3 -c "
import json, glob
path = glob.glob('preprocess/documents/*/jobs/paragraphs/' + '$PARAGRAPH_ID' + '/draft.json')[0]
print(json.load(open(path))['segments'][0]['id'])
")
```

### 4. Tokenize and review one segment

```shell
uv run wenyan preprocess tokenize-segment sunzi-bingfa --segment "$SEGMENT_ID"
uv run wenyan preprocess review-segment-tokenization sunzi-bingfa --segment "$SEGMENT_ID"
```

### 5. Check integrity

```shell
uv run wenyan preprocess validate-artifacts sunzi-bingfa
```

Committed artifacts under `preprocess/documents/` let CI resume or validate the pipeline without rerunning LLM jobs from scratch. After `package-document` runs, commit the matching tree under `content/documents/` so the reader has documents on a fresh checkout.

## Further reading

- [Editor workflow](architecture/preprocessing/editor-workflow.md) — full editorial journey
- [CLI spec](architecture/cli-spec.md) — commands, options, and status payloads
- [Preprocessing overview](architecture/preprocessing/README.md) — pipeline stages and design principles

Several later-stage commands (`gloss-segment`, `package-document`, `run`, etc.) are registered but not yet implemented in the current vertical slice.
