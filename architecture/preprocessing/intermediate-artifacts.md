# Intermediate Artifacts

## Purpose

Keep intermediate artifacts outside the reader package. These files make the preprocessing pipeline resumable, auditable, and easier to debug.

The reader should consume only the final validated package files.

## Workspace Roots

- `preprocess/documents/<document-id>/` — all intermediate artifacts described in this document.
- `content/documents/<document-id>/` — validated reader package files. See [Storage Format](../storage-format.md).

Paths below are relative to `preprocess/documents/<document-id>/` unless noted otherwise.

## Metadata And Effective Status

Output artifacts embed job metadata such as `inputHash`, `promptVersion`, `model`, and `attempts` in a documented header or envelope field.

Intermediate JSON files may also store `status` and failure reports. This metadata is useful for audit history and rerun decisions, but it should not be the sole source of truth for current pipeline progress.

Effective status should be derived from the artifact graph on disk:

- If an expected output artifact is missing, that component is pending.
- If an output artifact exists but one of its declared inputs is missing, changed, or produced by an incompatible prompt version, the output is stale.
- If an editor deletes an artifact to reject it, status should reflect that deletion immediately without requiring the editor to update job metadata by hand.

## Atomic Writes And Partial Failures

Artifact-producing commands should avoid writing final output paths until a component has fully succeeded. This prevents an interrupted LLM call, parser failure, or validation failure from leaving files that make status look complete.

Required write behavior:

- Write generated content to temporary paths first.
- Parse and validate temporary artifacts before promoting them.
- Promote temporary artifacts to final paths with an atomic rename when possible.
- Write a final artifact only when all required outputs for that component are present and internally consistent.
- Store raw failed responses or diagnostics under `raw-llm/` or a failure report path that status does not count as a completed component.
- Treat leftover temporary files as invalid or ignored during status and artifact validation.

Commands that produce multiple coupled artifacts should promote them as a unit. For example, `split-segments` should not leave segment `input.json` files pointing at missing paragraph drafts. If the full set cannot be promoted consistently, the command should leave the component pending or failed, not partially complete.

## Directory Shape

```text
preprocess/documents/document-id/
  normalized-document.json
  normalized-text.txt
  structure/
    chapter-proposal.json
    chapter-proposal.validation.json
    chapters/
      chapter-id/
        paragraph-proposal.json
        paragraph-proposal.validation.json
        summary.json
  indexes/
    entity-index.json
    term-index.json
    glossary-draft.json
  jobs/
    paragraphs/
      paragraph-id/
        draft.json
        validation.json
        review.json
        raw-llm/
    segments/
      segment-id/
        input.json
        tokenization.json
        tokenization-review.json
        glosses.json
        gloss-review.json
        grammar-notes.json
        grammar-review.json
        context-notes.json
        context-review.json
        raw-llm/
    assembly/
      paragraph-id/
        package.json
        validation.json
        review.json
    package/
      validation.json
```

Segment subjob outputs are the resumability unit. The paragraph assembler reads accepted segment subjob outputs directly when building the final paragraph package.

## Normalized Document

`normalized-document.json` is produced by deterministic normalization over the full document.

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "title": "三國志",
  "sourceHash": "sha256:...",
  "normalizedHash": "sha256:...",
  "textPath": "normalized-text.txt",
  "characterCount": 5238091,
  "textIndex": {
    "stride": 65536,
    "byteOffsets": [0, 196832, ...]
  },
  "normalization": {
    "encoding": "utf-8",
    "punctuationPolicy": "preserve-source",
    "notes": []
  }
}
```

The normalized text itself lives in a sibling sidecar file (`normalized-text.txt` by default). The manifest stays small; jobs read only the character spans they need via the byte-offset index. Ingest streams source text into the sidecar without holding the full document in memory.

## Chapter Proposal

`chapter-proposal.json` records editor-agreed chapter boundaries. It is written interactively (see the `preparing-source-structure` project skill), not by a preprocessing CLI command.

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "model": "editor",
  "promptVersion": "editor-chapter-structure-v1",
  "sourceHash": "sha256:...",
  "inputHash": "sha256:...",
  "chapters": [
    {
      "id": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
      "title": "卷一",
      "start": 0,
      "end": 5238,
      "rationale": "Opening chapter boundary follows the source heading."
    }
  ]
}
```

Deterministic span validation is written to a sibling file, not embedded in the proposal:

- `structure/chapter-proposal.validation.json`

## Paragraph Proposal

`paragraph-proposal.json` is produced by an LLM pass over one chapter.

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "model": "claude-opus-4.8",
  "promptVersion": "paragraph-structure-v1",
  "chapterTextHash": "sha256:...",
  "paragraphs": [
    {
      "id": "c777d984-afd6-4a31-aa34-2d26d29fb445",
      "start": 0,
      "end": 172,
      "rationale": "Coherent opening scene and first exchange."
    }
  ]
}
```

Deterministic span validation is written to a sibling file:

- `structure/chapters/chapter-id/paragraph-proposal.validation.json`

## Chapter Summary

`summary.json` gives paragraph structure jobs and focused segment subjobs compact chapter-level context.

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "model": "claude-opus-4.8",
  "promptVersion": "chapter-summary-v1",
  "summary": "Brief summary of the chapter's narrative, argument, people, and setting.",
  "entities": [
    {
      "surface": "曹操",
      "description": "Central political and military figure in the chapter."
    }
  ],
  "terms": [
    {
      "surface": "詔",
      "description": "Imperial command or edict."
    }
  ]
}
```

## Paragraph Structure Job

`split-segments` produces the paragraph draft, segment reconstruction validation, and per-segment `input.json` files. Job metadata is embedded in those output artifacts.

## Paragraph Draft

`paragraphs/paragraph-id/draft.json` is the parsed structured output from the paragraph-level model call. It contains segment shells and optional paragraph-level context notes, not tokenization, glosses, or grammar notes.

```json
{
  "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "segments": [
    {
      "id": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
      "text": "孟子見梁惠王。"
    }
  ],
  "paragraphContextNotes": [
    {
      "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
      "anchorSegmentIds": ["d70e05cc-a271-43e6-9abd-40c97c83bb96"],
      "body": "Paragraph-level context that applies across one or more segments.",
      "sources": ["src-001"]
    }
  ],
  "draftRationale": {
    "segmentation": "Single short sentence.",
    "paragraphContext": []
  }
}
```

## Segment Subjob Input

`segments/segment-id/input.json` is the minimal context shared by focused segment subjobs. This file is the primary resumable input for focused segment processing.

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "chapterId": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "segmentText": "孟子見梁惠王。",
  "localContext": {
    "paragraphSummary": "Only the context needed to interpret this segment.",
    "previousSegment": null,
    "nextSegment": "王曰：叟，不遠千里而來..."
  },
  "candidateGlosses": [
    {
      "id": "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
      "surface": "孟子",
      "pinyin": "Mengzi",
      "gloss": "Mencius"
    }
  ],
  "sourceSnippets": [
    {
      "id": "src-001",
      "label": "Mencius 1A1",
      "text": "Source or commentary excerpt used for grounding."
    }
  ]
}
```

## Segment Subjob Outputs

Each focused segment command writes its own artifact so tokenization, glossing, grammar annotation, context annotation, and their reviews can resume independently.

`segments/segment-id/tokenization.json`:

```json
{
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "text": "孟子見梁惠王。",
  "tokens": [
    {
      "id": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
      "surface": "孟子",
      "start": 0,
      "end": 2
    }
  ]
}
```

`segments/segment-id/glosses.json`:

```json
{
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "glossDecisions": [
    {
      "tokenId": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
      "glossId": "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
      "decision": "reuse-existing"
    }
  ],
  "newGlossIds": ["7d0d9c78-8307-4f11-9352-63b5d74af0fd"],
  "newGlosses": []
}
```

`segments/segment-id/grammar-notes.json`:

```json
{
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "grammarNotes": [
    {
      "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
      "type": "grammar",
      "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
      "body": "見 here is used in the sense of having an audience with a superior."
    }
  ]
}
```

`segments/segment-id/context-notes.json`:

```json
{
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "contextNotes": [
    {
      "id": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
      "type": "context",
      "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
      "body": "Mencius is being introduced in an audience with a ruler.",
      "sources": [
        {
          "sourceId": "src-001",
          "label": "Mencius 1A1",
          "detail": "Used to verify the immediate passage context."
        }
      ]
    }
  ]
}
```

## Paragraph Assembly

Paragraph assembly is two explicit commands that mirror the segment draft/review pattern:

```text
all segment subjobs complete (×8 per segment)
  → assemble-paragraph          # deterministic compile + validation
  → review-paragraph-assembly   # LLM review
  → package-document            # promotes approved packages to content/ (stubbed)
```

`assemble-paragraph` deterministically joins the paragraph draft and accepted segment subjob outputs into a reader-shaped `package.json` under `jobs/assembly/paragraph-id/`. `review-paragraph-assembly` writes `review.json` only; it does not write to `content/`. A paragraph is not complete until both assembly steps pass.

Deleting or changing any segment subjob output invalidates `package.json`, `validation.json`, and `review.json` for that paragraph. See [CLI Spec](../cli-spec.md) for command behavior.

## Paragraph Assembly Package (`package.json`)

`jobs/assembly/paragraph-id/package.json` is the staged paragraph package. It uses the same schema as the final paragraph file in [Storage Format](../storage-format.md). Job metadata fields (`model`, `inputHash`, `attempts`) are not stored on this file.

```json
{
  "id": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "segments": [
    {
      "id": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
      "text": "孟子見梁惠王。",
      "newGlossIds": ["7d0d9c78-8307-4f11-9352-63b5d74af0fd"],
      "tokens": [
        {
          "id": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
          "surface": "孟子",
          "start": 0,
          "end": 2,
          "glossId": "7d0d9c78-8307-4f11-9352-63b5d74af0fd"
        }
      ],
      "notes": []
    }
  ]
}
```

When `package-document` is implemented, approved `package.json` files promote to `content/documents/document-id/chapters/chapter-id/paragraphs/paragraph-id.json`.

## Segment Review Reports

Focused segment review reports are produced by focused LLM review passes, such as `tokenization-review.json`, `gloss-review.json`, `grammar-review.json`, and `context-review.json`.

```json
{
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "model": "claude-opus-4.8",
  "promptVersion": "review-segment-gloss-v1",
  "status": "approved",
  "findings": [],
  "requiredFixes": [],
  "sourceGrounding": [
    {
      "noteId": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
      "supported": true,
      "sourceIds": ["src-001"]
    }
  ]
}
```

## Blocked Component Report

When review rejects output, the focused component is marked blocked. The review artifact records the reason and any required fixes.

```json
{
  "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
  "status": "blocked",
  "reason": "Reviewer rejected gloss sense selection for 之.",
  "attempts": 1,
  "requiredFixes": [
    {
      "severity": "error",
      "message": "The selected gloss treats 之 as possessive, but the local syntax requires an object pronoun.",
      "target": {
        "tokenId": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
      }
    }
  ]
}
```
