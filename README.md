# Wenyan Reader

A local reader for Classical Chinese (文言文). Learners read one segment at a time and reveal glosses (pinyin + English) or grammar and context notes on demand.

The content is made ahead of time. A preprocessing CLI, with LLM and agent help, turns a full source text into a validated reader package. The reader app only reads those files and never calls an LLM.

| Part | State |
|---|---|
| Preprocessing CLI (`wenyan preprocess`) | Works end to end: ingest → paragraphs → segments → tokens/glosses/grammar → assembly → package. Context notes are written with agent skills. |
| Reader web app | Not started. |

Example document: [孫子兵法](sources/documents/sunzi-bingfa/) (`sunzi-bingfa`), partially processed in `preprocess/` and `content/`.

## Setup

Requires [uv](https://docs.astral.sh/uv/) (Python 3.12+).

```shell
uv sync
cp .env.example .env   # optional: choose a live model provider
```

The default provider is `mock` (fixtures, no API key). For live calls set `WENYAN_MODEL_PROVIDER` to `minimax` (cheaper, for development) or `anthropic`, plus the matching `*_API_KEY`. `.env` is gitignored and loaded automatically.

## Quickstart

```shell
uv run wenyan preprocess ingest-document sources/documents/sunzi-bingfa
uv run wenyan preprocess status sunzi-bingfa

# chapters are defined with the preparing-source-structure agent skill, then:
uv run wenyan preprocess split-paragraphs sunzi-bingfa --chapter 1
uv run wenyan preprocess split-segments  sunzi-bingfa --chapter 1 --paragraph 1
uv run wenyan preprocess run             sunzi-bingfa          # next segment, all LLM components
uv run wenyan preprocess status          sunzi-bingfa --chapter 1 --paragraph 1 --segment 1
```

After context notes are drafted and every segment in the paragraph is complete:

```shell
uv run wenyan preprocess assemble-paragraph sunzi-bingfa --chapter 1 --paragraph 1
uv run wenyan preprocess package-document   sunzi-bingfa
```

Walkthrough: [Editor Guide](docs/product/editor-guide.md). All commands: [CLI](docs/spec/cli.md).

## Repo map

| Path | Contents |
|---|---|
| `src/wenyan/` | Preprocessing CLI |
| `packages/wenyan-models/` | Shared Pydantic models (artifacts, reader package, status) |
| `prompts/` | LLM prompt templates |
| `sources/` | Source texts and registry |
| `preprocess/` | Intermediate artifacts (committed) |
| `content/` | Reader packages (committed) |
| `.opencode/skills/` | Agent skills for chapter structure and context notes |
| `docs/` | [Docs wiki](docs/index.md) |

## Development

```shell
uv run ruff check packages/wenyan-models/src src/wenyan tests
uv run mypy packages/wenyan-models/src src/wenyan
uv run python -m pytest
```

CI runs the same three. Tests never call a live LLM.

## Roadmap

See the [backlog](docs/backlog.md). Next up: the reader web app, structured LLM output, and deterministic checks for segment reconstruction, token offsets, and staleness.
