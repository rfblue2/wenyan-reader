# CLI Spec

## Purpose

Define the command-line interface for local preprocessing. The CLI is the editor-facing control surface for ingesting documents, running focused preprocessing jobs, inspecting progress, and packaging validated reader content.

This spec currently covers preprocessing only.

## Workspace Roots

Preprocessing uses two on-disk roots:

- `preprocess/documents/<document-id>/` — intermediate artifacts, job outputs, validation reports, and diagnostics. Paths in this spec are relative to this root unless noted otherwise.
- `content/documents/<document-id>/` — validated reader package files consumed by the app (`document.json`, `glosses/index.json`, `chapters/`, etc.). See [Storage Format](storage-format.md).

Commands accept `<document-id>` as a UUID or as a source slug resolved through `sources/registry.yaml`.

## Command Shape

All preprocessing commands live under:

```shell
wenyan preprocess <command>
```

Commands that perform preprocessing should use verbs:

```shell
wenyan preprocess ingest-document <document-source>
wenyan preprocess split-paragraphs <document-id> --chapter <chapter-id>
wenyan preprocess split-segments <document-id> --paragraph <paragraph-id>
wenyan preprocess review-paragraph-structure <document-id> --paragraph <paragraph-id>
wenyan preprocess tokenize-segment <document-id> --segment <segment-id>
wenyan preprocess review-segment-tokenization <document-id> --segment <segment-id>
wenyan preprocess gloss-segment <document-id> --segment <segment-id>
wenyan preprocess review-segment-gloss <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-grammar <document-id> --segment <segment-id>
wenyan preprocess review-segment-grammar <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-context <document-id> --segment <segment-id>
wenyan preprocess review-segment-context <document-id> --segment <segment-id>
wenyan preprocess assemble-paragraph <document-id> --paragraph <paragraph-id>
wenyan preprocess package-document <document-id>
```

Read-only inspection commands can use nouns when that reads more naturally:

```shell
wenyan preprocess status <document-id>
wenyan preprocess validate-artifacts <document-id>
wenyan preprocess prune <document-id>
wenyan preprocess review-report <document-id> --segment <segment-id>
```

## Common Behavior

Every artifact-producing command should:

- Be safe to rerun.
- Reuse successful artifacts when the input hash and prompt version are unchanged.
- Write intermediate artifacts before writing final reader package files.
- Write each logical output atomically: produce temporary files first, validate them, then rename them into their final paths only after the command has all required outputs for that component.
- Record job kind, input hash, prompt version, model, status, output path, and failure report when applicable.
- Stop on validation or review failures unless the command explicitly supports continuing through blocked units.

If an LLM call or parser fails partway through a command, the command should leave no final output artifact for that component. It may write a failure report or raw diagnostic artifact, but it must not write a final artifact that status could mistake for complete.

Status should be derived from the artifact graph on disk, not from an independent source of truth. If an editor deletes an artifact they are unhappy with, the next `status` call should reflect that deletion immediately:

- The deleted component becomes `pending`.
- Any downstream artifact that depends on the deleted component becomes `stale` or `blocked-by-upstream`, even if its file still exists.
- A rerun should regenerate only the missing or stale component and the downstream artifacts that consume it.

Common options:

- `--force`: rerun even when a successful matching artifact already exists.
- `--dry-run`: show what would run without writing artifacts.
- `--json`: emit machine-readable output.
- `--concurrency <n>`: cap parallel execution where a command supports fan-out.
- `--continue-on-blocked`: continue batch execution when one unit becomes blocked.

### Unit reference resolution

Scoped commands accept stable UUIDs or editor-friendly ordinals:

- `--chapter`: UUID, number (e.g. `1`), or title (e.g. `始計第一`).
- `--paragraph`: UUID, or number when `--chapter` is also set.
- `--segment`: UUID, or number when `--paragraph` is also set (and `--chapter` when the paragraph is numeric).

When a command accepts both `--segment` and `--paragraph`, they play different roles:

- `--segment` selects a single segment. Any `--chapter` / `--paragraph` values disambiguate ordinal segment numbers (for example `--chapter 1 --paragraph 1 --segment 1`).
- `--paragraph` without `--segment` selects a paragraph batch (all pending segments under that paragraph).

Resolution is shared across commands via `wenyan.cli.status_scope` and `wenyan.cli.unit_refs`.

## Command Reference

### `ingest-document`

```shell
wenyan preprocess ingest-document <document-source>
```

Scope: document source directory.

Reads raw source text and metadata, creates or verifies the stable `documentId`, normalizes text, computes source and normalized hashes, writes `normalized-document.json`, and initializes the preprocessing artifact directory.

Primary output:

- `preprocess/documents/document-id/normalized-document.json`

Chapter structure is prepared interactively before downstream preprocessing. See the `preparing-source-structure` project skill and `structure/chapter-proposal.json` in [Intermediate Artifacts](preprocessing/intermediate-artifacts.md).

### `split-paragraphs`

```shell
wenyan preprocess split-paragraphs <document-id> --chapter <chapter-id>
```

Scope: one chapter.

Builds a chapter-level paragraph-discovery prompt, proposes paragraph spans, generates or updates chapter summary and chapter-local indexes, and validates that paragraph spans reconstruct the chapter exactly.

Primary outputs:

- `structure/chapters/chapter-id/paragraph-proposal.json`
- `structure/chapters/chapter-id/paragraph-proposal.validation.json`
- `structure/chapters/chapter-id/summary.json`

### `split-segments`

```shell
wenyan preprocess split-segments <document-id> --paragraph <paragraph-id>
```

Scope: one paragraph.

Builds bounded paragraph context, proposes reader segment boundaries, drafts paragraph-level context notes only when they apply across segments, validates that segment strings reconstruct the paragraph, and creates focused segment subjob inputs.

Primary outputs:

- `jobs/paragraphs/paragraph-id/draft.json`
- `jobs/paragraphs/paragraph-id/validation.json`
- `jobs/segments/segment-id/input.json`

### `review-paragraph-structure`

```shell
wenyan preprocess review-paragraph-structure <document-id> --paragraph <paragraph-id>
```

Scope: one paragraph structure output.

Reviews segment boundaries, paragraph-level context notes, and pedagogical segmentation quality.

Primary output:

- `jobs/paragraphs/paragraph-id/review.json`

### `tokenize-segment`

```shell
wenyan preprocess tokenize-segment <document-id> --segment <segment-id>
wenyan preprocess tokenize-segment <document-id> --paragraph <paragraph-id>
```

Scope: one segment, or pending segments under one paragraph.

Identifies glossable token occurrences and offsets. This is the shared prerequisite for gloss, grammar, and segment-local context annotation.

Primary output:

- `jobs/segments/segment-id/tokenization.json`

### `review-segment-tokenization`

```shell
wenyan preprocess review-segment-tokenization <document-id> --segment <segment-id>
```

Scope: one segment tokenization output.

Reviews token boundaries for correctness, useful multi-character grouping, and offset fidelity.

Primary output:

- `jobs/segments/segment-id/tokenization-review.json`

### `gloss-segment`

```shell
wenyan preprocess gloss-segment <document-id> --segment <segment-id>
wenyan preprocess gloss-segment <document-id> --paragraph <paragraph-id>
```

Scope: one segment, or pending segments under one paragraph.

Selects existing document-level glosses or proposes new glosses for reviewed token occurrences.

Primary output:

- `jobs/segments/segment-id/glosses.json`

### `review-segment-gloss`

```shell
wenyan preprocess review-segment-gloss <document-id> --segment <segment-id>
```

Scope: one segment gloss output.

Reviews gloss sense selection, pinyin, homonym/polysemy handling, and whether proposed new glosses duplicate existing entries.

Primary output:

- `jobs/segments/segment-id/gloss-review.json`

### `annotate-segment-grammar`

```shell
wenyan preprocess annotate-segment-grammar <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-grammar <document-id> --paragraph <paragraph-id>
```

Scope: one segment, or pending segments under one paragraph.

Drafts grammar notes anchored to segment tokens. This can run after tokenization review and does not need to wait for gloss or context note jobs.

Primary output:

- `jobs/segments/segment-id/grammar-notes.json`

### `review-segment-grammar`

```shell
wenyan preprocess review-segment-grammar <document-id> --segment <segment-id>
```

Scope: one segment grammar output.

Reviews whether grammar notes describe constructions actually present, are anchored correctly, and are useful for comprehension.

Primary output:

- `jobs/segments/segment-id/grammar-review.json`

### `annotate-segment-context`

```shell
wenyan preprocess annotate-segment-context <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-context <document-id> --paragraph <paragraph-id>
```

Scope: one segment, or pending segments under one paragraph.

**Stubbed.** Returns `not-implemented` and points to `.cursor/skills/drafting-context-notes/SKILL.md`. Use that skill to write `context-notes.json` with inline citations.

Primary output:

- `jobs/segments/segment-id/context-notes.json`

### `review-segment-context`

```shell
wenyan preprocess review-segment-context <document-id> --segment <segment-id>
```

Scope: one segment context output.

**Stubbed.** Returns `not-implemented` and points to `.cursor/skills/reviewing-context-notes/SKILL.md`.

Primary output:

- `jobs/segments/segment-id/context-review.json`

### `assemble-paragraph`

```shell
wenyan preprocess assemble-paragraph <document-id> --paragraph <paragraph-id>
```

Scope: one paragraph.

Combines paragraph structure and completed segment outputs, validates paragraph reconstruction and final paragraph shape, runs paragraph package review, and writes the final paragraph file when accepted.

Primary outputs:

- `jobs/assembly/paragraph-id/validation.json`
- `jobs/assembly/paragraph-id/review.json`
- `content/documents/document-id/chapters/chapter-id/paragraphs/paragraph-id.json`

### `package-document`

```shell
wenyan preprocess package-document <document-id>
```

Scope: one document.

Builds final reader package files, validates reachability and schema shape, and reports blocked or incomplete units.

Primary outputs (under `content/documents/document-id/`):

- `document.json`
- `glosses/index.json`
- `chapters/*/chapter.json`
- `chapters/*/paragraphs/*.json`

Also runs document-level consistency review before promoting package files.

### `run`

```shell
wenyan preprocess run <document-id>
wenyan preprocess run <document-id> --next-segment
wenyan preprocess run <document-id> --segment <segment-id>
wenyan preprocess run <document-id> --next-paragraph
```

Scope: one segment (default), one named segment, or one paragraph structure pass.

Runs preprocessing commands in dependency order. With no segment flags, processes the next incomplete segment through all segment subjobs (tokenization, gloss, grammar, context, and each review pass). Reuses successful artifacts, stops at validation or review failures, and stops with a clear error when a required subjob command is not implemented yet.

`--next-paragraph` runs `split-segments` once for the first paragraph that lacks a segment draft.

### `status`

```shell
wenyan preprocess status <document-id>
wenyan preprocess status <document-id> --chapter <chapter-id>
wenyan preprocess status <document-id> --paragraph <paragraph-id>
wenyan preprocess status <document-id> --segment <segment-id> [--chapter <ref>] [--paragraph <ref>] [--json]
```

Scope: document, chapter, paragraph, or segment.

Reports progress for the next level down:

- Document status lists chapters.
- Chapter status lists paragraphs.
- Paragraph status lists segments.
- Segment status shows the segment source text and generated artifacts in an editor-friendly terminal layout:
  - Location header with chapter/paragraph/segment handles (ordinals when resolvable) and UUIDs.
  - Gloss table joining token surfaces with pinyin, gloss text, and reuse/create decisions when `glosses.json` exists; token surfaces only when only tokenization exists.
  - Grammar and context notes when present.
  - Review status and findings for each present review artifact.
  - Component summary for all eight segment subjobs.

Use `--json` at segment scope for a structured `SegmentShowView` payload suitable for agents and tooling.

Status output should include a compact rollup of complete, in-progress, pending, failed, and blocked units, plus the last validation or review error per failed or blocked unit.

Status should also recognize stale downstream artifacts. An artifact is stale when one of its declared inputs is missing, has a different input hash, or was produced with an incompatible prompt version. Stale artifacts should not count as complete.

### `validate-artifacts`

```shell
wenyan preprocess validate-artifacts <document-id>
wenyan preprocess validate-artifacts <document-id> --chapter <chapter-id>
wenyan preprocess validate-artifacts <document-id> --paragraph <paragraph-id>
wenyan preprocess validate-artifacts <document-id> --segment <segment-id>
```

Scope: document, chapter, paragraph, or segment.

Checks artifact graph integrity without generating new content. This command is stricter than `status`: `status` summarizes progress, while `validate-artifacts` reports structural problems that could make progress misleading.

Validation should check:

- All expected artifacts for the selected scope are present or explicitly pending.
- Every present artifact is valid JSON and matches the expected schema for its artifact type.
- Every artifact's declared input hashes match the current upstream artifacts.
- No artifact points to a missing segment, paragraph, chapter, source snippet, note, token, or gloss.
- No downstream artifact is marked complete when an upstream dependency is missing or stale.
- No final reader package file references missing preprocessing artifacts or missing package files.
- No temporary output file is being treated as a real artifact.

The command should return a non-zero exit code when it finds invalid, dangling, stale, or partially written artifacts.

### `prune`

```shell
wenyan preprocess prune <document-id> [--dry-run] [--json]
```

Scope: document.

Removes orphaned segment job directories under `jobs/segments/`. A segment is orphaned when its directory exists on disk but its ID is not listed in any current paragraph draft for a paragraph still present in the structure proposals. This typically happens after `split-paragraphs` or `split-segments` is rerun with new boundaries, leaving stale preprocessing artifacts behind.

With `--dry-run`, lists the directories that would be removed without deleting them. When nothing is orphaned, exits zero and reports `no orphaned segments`.

### `review-report`

```shell
wenyan preprocess review-report <document-id> --segment <segment-id>
```

Scope: one reviewed unit.

Prints the latest review report for the selected segment or focused component.

## Sample Status Payloads

The CLI should support a machine-readable status payload, even if the default terminal output is friendlier. Status is a progress tracker rather than just a job table. Each scope should show the status of the next level down.

Document-level status lists chapters:

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "title": "三國志",
  "scope": {
    "type": "document"
  },
  "source": {
    "status": "normalized",
    "normalizedDocumentPath": "preprocess/documents/9ad841a6-f20f-4f43-9805-166ab2d98e7f/normalized-document.json",
    "sourceHash": "sha256:...",
    "normalizedHash": "sha256:..."
  },
  "counts": {
    "chapters": 12,
    "complete": 1,
    "inProgress": 1,
    "pending": 10,
    "failed": 0,
    "blocked": 0
  },
  "chapters": [
    {
      "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
      "title": "卷一",
      "status": "in-progress",
      "progress": {
        "paragraphsComplete": 8,
        "paragraphsTotal": 42
      }
    },
    {
      "chapterId": "2866c62f-7cb7-4e35-a6f0-9f61c9942b3b",
      "title": "卷二",
      "status": "pending",
      "progress": {
        "paragraphsComplete": 0,
        "paragraphsTotal": null
      }
    }
  ]
}
```

Chapter-level status lists paragraphs:

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "scope": {
    "type": "chapter"
  },
  "counts": {
    "paragraphs": 42,
    "complete": 8,
    "inProgress": 1,
    "pending": 33,
    "failed": 0,
    "blocked": 0
  },
  "paragraphs": [
    {
      "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
      "ordinal": 1,
      "status": "in-progress",
      "progress": {
        "segmentsComplete": 3,
        "segmentsTotal": 4
      }
    },
    {
      "paragraphId": "312d1efe-b5a6-4c37-9a15-cc8e8032f0c6",
      "ordinal": 2,
      "status": "pending",
      "progress": {
        "segmentsComplete": 0,
        "segmentsTotal": null
      }
    }
  ]
}
```

Paragraph-level status lists segments:

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "scope": {
    "type": "paragraph"
  },
  "structure": {
    "status": "complete",
    "segmentCount": 4
  },
  "counts": {
    "segments": 4,
    "complete": 3,
    "inProgress": 0,
    "pending": 0,
    "failed": 0,
    "blocked": 1
  },
  "segments": [
    {
      "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
      "ordinal": 1,
      "status": "blocked",
      "textPreview": "孟子見梁惠王。",
      "progress": {
        "componentsComplete": 6,
        "componentsTotal": 8
      },
      "blockedComponent": "review-segment-gloss"
    },
    {
      "segmentId": "582b4096-0a68-4de0-bebf-5f9cb0fc3c1a",
      "ordinal": 2,
      "status": "complete",
      "textPreview": "王曰：叟，不遠千里而來...",
      "progress": {
        "componentsComplete": 8,
        "componentsTotal": 8
      }
    }
  ]
}
```

Segment-level status returns a `SegmentShowView` with source text, tokens, notes, reviews, and components:

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "documentRef": "mengzi",
  "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "chapterHandle": "1",
  "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "paragraphHandle": "1",
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "segmentHandle": "1",
  "text": "孟子見梁惠王。",
  "status": "blocked",
  "tokens": [],
  "grammarNotes": [],
  "contextNotes": [],
  "reviews": [],
  "components": [
    {
      "kind": "tokenize-segment",
      "status": "complete",
      "artifactPath": "preprocess/documents/9ad841a6-f20f-4f43-9805-166ab2d98e7f/jobs/segments/d70e05cc-a271-43e6-9abd-40c97c83bb96/tokenization.json"
    },
    {
      "kind": "review-segment-tokenization",
      "status": "complete",
      "artifactPath": "preprocess/documents/9ad841a6-f20f-4f43-9805-166ab2d98e7f/jobs/segments/d70e05cc-a271-43e6-9abd-40c97c83bb96/tokenization-review.json"
    },
    {
      "kind": "gloss-segment",
      "status": "complete",
      "artifactPath": "preprocess/documents/9ad841a6-f20f-4f43-9805-166ab2d98e7f/jobs/segments/d70e05cc-a271-43e6-9abd-40c97c83bb96/glosses.json"
    },
    {
      "kind": "review-segment-gloss",
      "status": "blocked",
      "attempts": 3,
      "artifactPath": "preprocess/documents/9ad841a6-f20f-4f43-9805-166ab2d98e7f/jobs/segments/d70e05cc-a271-43e6-9abd-40c97c83bb96/gloss-review.json",
      "blockedReason": "Reviewer repeatedly rejected gloss sense selection for 之.",
      "requiredFixes": [
        {
          "severity": "error",
          "message": "The selected gloss treats 之 as possessive, but the local syntax requires an object pronoun.",
          "target": {
            "tokenId": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
          }
        }
      ]
    },
    {
      "kind": "annotate-segment-grammar",
      "status": "pending"
    },
    {
      "kind": "review-segment-grammar",
      "status": "pending"
    },
    {
      "kind": "annotate-segment-context",
      "status": "pending"
    },
    {
      "kind": "review-segment-context",
      "status": "pending"
    }
  ]
}
```

## Related Docs

- [CLI Tech Stack](tech-stack/cli.md)
- [Preprocessing](preprocessing/README.md)
