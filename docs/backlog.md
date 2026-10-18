# Backlog

Planned features and known gaps. Specs describe current behavior only; anything intended but not built lives here. Detailed designs go in [proposals](proposals/).

When asked what to work on next, start here and cross-check against the tree (`status`, tests, recent commits).

**Priority:** P1 next up · P2 soon · P3 later.

## Features

| # | Item | P | Notes |
|---|---|---|---|
| F1 | **Reader web app** | P1 | Consume `content/`; UX in [Reader UX](product/reader-ux.md); stack undecided ([Web App](architecture/webapp.md)). |
| F2 | **Automated context notes** | P2 | Replace stub commands and skills with a tool-enabled model that cites sources. Keep the current artifact shapes; set `model` to the real id. |
| F3 | **Preprocessor CI** | P2 | Run `validate-artifacts` and package checks on committed `preprocess/` and `content/`. Depends on G-V1. |
| F4 | **Document / PDF export** | P3 | Export curated documents from packaged content. |
| F5 | **Per-role model routing** | P2 | Draft / review / structure roles with dev and prod profiles, so reviews are not self-review by the drafting model. Optional long-context model for chapter-scale work. [Proposal](proposals/model-routing.md). |
| F6 | **Structured output enforcement** | P1 | [LLM output correctness](proposals/llm-output-correctness.md) phases 1–4. Fixes gloss id linking. |
| F7 | **Bounded job context** | P3 | Chapter `summary.json`, entity/term indexes, neighbor-paragraph window, populated `localContext` in segment input. [Proposal](proposals/job-execution.md). |
| F8 | **Lexicon lookup** | P3 | Use deterministic dictionaries before LLM gloss calls. [Proposal](proposals/model-routing.md). |
| F9 | **Document consistency review** | P3 | Check recurring names, gloss duplication, and first-occurrence order across the document at package time. |

## Correctness gaps

| # | Gap | P | Notes |
|---|---|---|---|
| G-C1 | Segment reconstruction not checked at split | P1 | `split-segments` writes `passed` with no checks; segment spans are never validated for contiguity or coverage. |
| G-C2 | Token offsets never checked | P1 | Verify `surface == text[start:end]`, order, non-overlap, and coverage of non-punctuation characters at promote time. |
| G-C3 | No staleness for segment drafts and reviews | P1 | Status ignores `inputHash` except for assembly. Hand-edited drafts leave approved reviews "complete". Rejected review with unchanged input skips with exit 0. [Proposal](proposals/artifact-graph-integrity.md). |
| G-C4 | No downstream invalidation | P2 | Re-tokenizing leaves glosses and grammar complete; deleting a draft shows its review `pending`, not stale. [Proposal](proposals/artifact-graph-integrity.md). |
| G-C5 | Prompt changes invalidate nothing | P2 | Add a prompt template hash to each job's `inputHash`. [Proposal](proposals/artifact-graph-integrity.md). |
| G-C6 | LLM-minted ids | P2 | Segment ids collide across paragraphs (on disk: `a1b2c3d4-…` in two drafts; `a8c3d5e7-…4d5e6` is not a UUID). Mint ids in code; keep ids stable for unchanged spans. |
| G-C7 | Glossary draft accumulates orphans | P2 | Gloss review merges on approval and never removes. Build at assembly/package time from approved artifacts; filter `glosses/index.json` to reachable entries. |
| G-C8 | Paragraph context notes unvalidated | P2 | Raw dicts with mixed `sources`; bad anchors raise at assembly. Type them and validate at split. |
| G-C9 | Chapter proposal not validated by code | P2 | No code checks chapter span coverage or contiguity; validation file is hand-written; `split-paragraphs` does not gate on it. Paragraph span order is not enforced (sorted first). |
| G-C10 | Reader package checks are shallow | P3 | No on-disk path/reachability checks, no document-wide id uniqueness; old `content/` files never removed. |
| G-C11 | Citation fields dropped | P3 | `url`/`accessedAt` lost at assembly. |
| G-C12 | Normalization policies not applied | P3 | `punctuationPolicy`, `encoding`, and `sourceHeadings` in `document.yaml` are recorded only. |

## CLI and workflow gaps

| # | Gap | P | Notes |
|---|---|---|---|
| G-V1 | `validate-artifacts` checks only the normalized document | P1 | Intended: schema, hash staleness, dangling refs, leftover `.tmp`, and package refs at every scope. [Proposal](proposals/artifact-graph-integrity.md). |
| G-W1 | `--dry-run` still calls the LLM | P2 | Should report what would run. `run --dry-run` can loop on `split-segments`. [Proposal](proposals/job-execution.md). |
| G-W2 | `run` gaps | P2 | Stops at the context stub every segment; `--paragraph` without `--segment` is ignored; never runs `split-paragraphs`. |
| G-W3 | No concurrency or `--continue-on-blocked` | P3 | `concurrency.default` config is unused; batches stop at the first failure. [Proposal](proposals/job-execution.md). |
| G-W4 | LLM errors surface as tracebacks | P2 | Catch HTTP/parse errors as `JobFailure`; keep raw responses under `raw-llm/`. Record `attempts` for real. [Proposal](proposals/job-execution.md). |
| G-W5 | Stub commands | P3 | Decide cut vs build: `review-paragraph-structure`, `review-report`. Context stubs exit 1, others exit 2. |
| G-W6 | Status rollups | P3 | Show last error at paragraph/chapter level; unknown slug in `status` raises a traceback. [Proposal](proposals/artifact-graph-integrity.md). |
| G-W7 | Merge segment reviews | P3 | One review call per segment with per-component verdicts instead of three. |
| G-W8 | `prune` gaps | P3 | Does not report removed assembly dirs; never removes assembly dirs for deleted paragraphs. |
| G-W9 | Batch writes not atomic | P3 | Multi-file promotion can leave partial sets; `.tmp` leftovers never cleaned. [Proposal](proposals/artifact-graph-integrity.md). |

## Housekeeping

| # | Item | P | Notes |
|---|---|---|---|
| H1 | **Audit and trim agent skills** | P2 | Skills moved from `.cursor/skills/` as-is. Remove duplication with the [CLI](spec/cli.md) and [Editor Guide](product/editor-guide.md); verify workflows. `preparing-source-structure` says to write `promptVersion`, which the schema rejects. |
| H2 | **DRY and simplify** | P2 | Reduce duplication in code and workflow. |
| H3 | Re-audit architecture and code | P3 | Redo the removed audits once the gaps above are triaged. |
| H6 | Code quality | P3 | Typed construction in `core/status/derivation.py`; wire `StatusReader`/`GraphValidator` through `JobContext`. |
| H7 | Missing tests | P3 | `split-segments` reconstruction failure; stale approved review; golden-file status payload tests. |
| H8 | Layering deviations | P3 | See [Coding Style — Known deviations](architecture/coding-style.md#known-deviations). |
| H9 | JSON Schema export | P3 | Export schemas from `wenyan-models` for the web app and non-Python validation. |
| H10 | CLI output consolidation | P3 | One mechanism for shared flags; route all rendering through one output module (Rich vs JSON); map exit codes in one place instead of ad-hoc `typer.Exit`. |
| H11 | Format check in CI | P3 | CI runs `ruff check` only; add `ruff format --check`. |
