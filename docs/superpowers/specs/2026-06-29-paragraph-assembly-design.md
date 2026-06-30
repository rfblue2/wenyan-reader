# Paragraph Assembly Design

> **Update (2026-06-29):** LLM `review-paragraph-assembly` was removed after implementation. Assembly is deterministic only; a paragraph is complete when `assemble-paragraph` validation passes.

## Summary

Implement paragraph assembly as an explicit preprocessing command: `assemble-paragraph` compiles accepted segment subjob outputs into a reader-shaped paragraph package under preprocess. Promotion to `content/documents/` is deferred to `package-document`. Extend paragraph status so a paragraph is not complete until assembly validation passes.

## Decisions

| Topic | Decision |
| --- | --- |
| Trigger | Explicit commands only; `run preprocess` completes the current segment through all eight subjobs and does not auto-assemble |
| Commands | Two: `assemble-paragraph` + `review-paragraph-assembly` |
| Staging | Compiled paragraph lives at `preprocess/.../jobs/assembly/<paragraph-id>/package.json` until `package-document` promotes it |
| Review side effects | Review writes `review.json` only; no write to `content/` on approval |
| Compile | Deterministic join of segment artifacts; no LLM in assemble |
| Status | Paragraph rollup requires structure complete, all segments complete, assembly draft current, and assembly review approved |
| Test backend | Mock LLM fixtures for review; compile tests use artifact fixtures only |

## Pipeline Position

```text
split-segments
  → segment subjobs (×8 per segment)
  → assemble-paragraph          # deterministic compile + validation
  → review-paragraph-assembly   # LLM review
  → package-document            # out of scope here; promotes approved packages to content/
```

## Commands

### `assemble-paragraph`

```shell
wenyan preprocess assemble-paragraph <document-id> --paragraph <paragraph-id>
```

Scope: one paragraph.

Compiles the paragraph draft and accepted segment subjob outputs into the reader paragraph package shape, runs deterministic validation, and writes assembly artifacts when checks pass.

Primary outputs:

- `jobs/assembly/paragraph-id/package.json`
- `jobs/assembly/paragraph-id/validation.json`

Prerequisites:

- `jobs/paragraphs/paragraph-id/draft.json` exists
- Every segment in the draft has all eight segment subjobs complete with approved reviews

Behavior:

- Skip when `package.json` is current (same computed input hash) unless `--force`
- Write to temporary paths, validate, then atomically promote
- Non-zero exit on validation failure; do not leave a promoted `package.json`

### `review-paragraph-assembly`

```shell
wenyan preprocess review-paragraph-assembly <document-id> --paragraph <paragraph-id>
```

Scope: one paragraph assembly output.

Reviews the assembled paragraph package for cross-segment consistency and pedagogical quality.

Primary output:

- `jobs/assembly/paragraph-id/review.json`

Prerequisites:

- Current `jobs/assembly/paragraph-id/package.json`

Behavior:

- Skip when review matches package `inputHash` unless `--force`
- Write review artifact; non-zero exit on rejection (`review-rejected`)
- Does not write to `content/`

## Artifacts

### Directory layout

```text
preprocess/documents/<document-id>/
  jobs/
    paragraphs/<paragraph-id>/
      draft.json
    segments/<segment-id>/
      tokenization.json
      glosses.json
      grammar-notes.json
      context-notes.json
      *-review.json
    assembly/<paragraph-id>/
      package.json
      validation.json
      review.json
```

### `package.json` (reader shape, preprocess staging)

Same schema as the final reader paragraph file documented in [storage-format.md](../../../architecture/storage-format.md). No job metadata fields (`model`, `inputHash`, `attempts`) on this file.

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
      "notes": [
        {
          "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
          "type": "grammar",
          "anchorTokenIds": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
          "body": "見 here is used in the sense of having an audience with a superior."
        },
        {
          "id": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
          "type": "context",
          "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
          "body": "Mencius is being introduced in an audience with a ruler.",
          "sources": [
            {
              "label": "Mencius 1A1",
              "detail": "Used to verify the immediate passage context."
            }
          ]
        }
      ]
    }
  ]
}
```

Required fields per segment: `id`, `text`, `newGlossIds`, `tokens`, `notes`.

Required fields per token: `id`, `surface`, `start`, `end`, `glossId`.

Required fields per note: `id`, `type`, `anchorTokenIds`, `body`. Optional: `sources` (reader shape uses `label` and `detail` only).

### `validation.json`

Reuse `ParagraphValidationArtifact` (`status`, `checks`) or a dedicated assembly validation model if additional envelope fields are needed. Checks include:

- All segments in draft have complete, approved subjob outputs
- Segment order and texts match `draft.json`
- Segment strings reconstruct the paragraph text
- Token offsets reconstruct each segment text
- Token IDs unique within each segment
- Every token has a resolvable `glossId`
- `newGlossIds` match glosses artifacts
- Note anchors reference tokens in the same segment
- Assembled package validates against `ParagraphPackage` Pydantic model

### `review.json`

Follow the segment review envelope:

```json
{
  "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "model": "claude-opus-4.8",
  "promptVersion": "review-paragraph-assembly-v1",
  "inputHash": "sha256:...",
  "attempts": 1,
  "status": "approved",
  "findings": [],
  "requiredFixes": []
}
```

Review checklist (from [review-and-quality-jobs.md](../../../architecture/preprocessing/review-and-quality-jobs.md)):

- The assembled paragraph still reads as the original paragraph
- Segment outputs are internally consistent when read together
- Paragraph-level context notes do not duplicate or conflict with segment-local notes
- New gloss introductions are pedagogically sensible in paragraph context

## Compile Logic

Add `src/wenyan/core/assembly/compile_paragraph.py` with a pure function:

```python
def compile_paragraph_package(
    draft: ParagraphDraft,
    segment_outputs: Sequence[CompiledSegmentInputs],
) -> ParagraphPackage: ...
```

For each segment in draft order:

1. Read `tokenization.json` tokens and attach `glossId` from `glosses.json` decisions
2. Copy `newGlossIds` from `glosses.json`
3. Merge `grammar-notes.json` entries into `notes[]` with `"type": "grammar"`
4. Merge `context-notes.json` entries into `notes[]` with `"type": "context"`, mapping sources to reader shape (`label`, `detail`; use `detail` from intermediate `detail` or `excerpt` when present)
5. Fold `paragraphContextNotes` from the draft into the first segment listed in each note's `anchorSegmentIds`; set `anchorTokenIds` to the glossable token with the lowest `start` offset in that segment (paragraph-level notes in the reader format still live inside a segment's `notes[]`)

Reuse gloss-resolution patterns from `core/show/segment_view.py` where practical. Keep show and compile separate: show is editor-facing; compile produces reader storage shape.

### Input hash for assembly skip/stale

Hash a stable JSON document containing:

- Paragraph draft content hash or serialized draft
- Per-segment hashes of accepted subjob outputs (tokenization, glosses, grammar notes, context notes)

When any upstream segment artifact changes or is deleted, assembly outputs become stale.

## Models And Ports

### `packages/wenyan-models`

| Addition | Purpose |
| --- | --- |
| `reader/paragraph.py` — `ParagraphPackage`, `ReaderSegment`, `ReaderToken`, `ReaderNote`, `ReaderNoteSource` | Final reader paragraph schema |
| `artifacts/assembly.py` — `ParagraphAssemblyReviewArtifact` | `review.json` envelope |
| `domain/enums.py` — `ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE` | New artifact kind for `package.json` |
| `domain/enums.py` — `ParagraphAssemblyKind` | `assemble-paragraph`, `review-paragraph-assembly` for status |
| `status/paragraph.py` — `ParagraphAssemblyStatus`, extend `ParagraphStatus` | Status payload |

### `src/wenyan/core/ports/artifact_ref.py`

Add `paragraph_assembly_package_ref(document_id, paragraph_id)`.

Existing refs for `validation.json` and `review.json` remain unchanged.

### `src/wenyan/core/adapters/paths.py`

Map `PARAGRAPH_ASSEMBLY_PACKAGE` to `jobs/assembly/<paragraph-id>/package.json`.

## Jobs

| Module | Responsibility |
| --- | --- |
| `jobs/assemble_paragraph.py` | Load draft + segment outputs, call compile, validate, write artifacts |
| `jobs/review_paragraph_assembly.py` | LLM review of `package.json`; mirror `review_segment_gloss.py` |

Wire CLI in `src/wenyan/cli/preprocess.py`. Remove the assemble-paragraph stub message.

Add prompt template `prompts/review-paragraph-assembly/` (or equivalent path under configured prompts root).

## Status

Extend `derive_paragraph_status` in `core/status/derivation.py`:

```json
{
  "structure": { "status": "complete", "segmentCount": 2 },
  "assembly": {
    "assemble": {
      "kind": "assemble-paragraph",
      "status": "complete",
      "artifactPath": "preprocess/documents/.../jobs/assembly/.../package.json"
    },
    "review": {
      "kind": "review-paragraph-assembly",
      "status": "pending"
    }
  },
  "counts": { "segments": 2, "complete": 2, "inProgress": 0, "pending": 0, "blocked": 0, "failed": 0 },
  "segments": [ "..." ]
}
```

### Rollup rules

| Condition | Paragraph `status` |
| --- | --- |
| Any segment blocked | `blocked` |
| Structure not complete | `pending` |
| Segments incomplete | `in-progress` |
| Segments complete, assembly not started or stale | `in-progress` |
| Assembly review rejected | `blocked` |
| Assembly draft missing after segments complete | `in-progress` (assemble = `pending`) |
| Assemble complete, review missing | `in-progress` |
| Assemble complete, review approved | `complete` |

Update `_rollup_paragraph_status`: remove the rule that marks a paragraph complete when all segments are complete.

Update `cli/status_output.py` paragraph renderer to show an Assembly section (assemble + review lines).

Chapter and document rollups inherit the new paragraph semantics automatically.

## `package-document` Contract (follow-up slice)

Not implemented in this slice, but assembly is designed for it:

- Require approved `review.json` for each paragraph being packaged
- Copy `jobs/assembly/<paragraph-id>/package.json` → `content/documents/<document-id>/chapters/<chapter-id>/paragraphs/<paragraph-id>.json`
- Build `document.json`, `chapter.json`, promote `indexes/glossary-draft.json` → `glosses/index.json`
- Run document-level validation and consistency review

Reuse `compile_paragraph_package` only for re-validation during package if needed; do not recompile from scratch unless assembly artifacts are missing.

## Stale And Prune

- Deleting or changing any segment subjob output invalidates `package.json`, `validation.json`, and `review.json` for that paragraph
- `prune` should remove stale assembly artifacts when upstream segment artifacts are pruned (extend existing prune rules)
- Document in [editor-workflow.md](../../../architecture/preprocessing/editor-workflow.md)

## Error Handling

| Condition | Behavior |
| --- | --- |
| Missing paragraph draft | `JobFailure` `missing-input` |
| Segment subjobs incomplete | `JobFailure` `blocked-upstream` with segment id |
| Compile/validation failure | `JobFailure` `validation-failed`; write `validation.json` with failed checks when useful |
| Missing `package.json` at review time | `JobFailure` `missing-input` |
| Review rejection | Write `review.json`, `JobFailure` `review-rejected` |
| `--dry-run` | Return promoted artifact without writing |
| `--force` | Ignore current-hash skip |

## Tests

| File | Covers |
| --- | --- |
| `tests/core/assembly/test_compile_paragraph.py` | Token+gloss join, note merge, paragraph context note folding, source shape |
| `tests/jobs/test_assemble_paragraph.py` | Happy path, skip on current hash, missing draft, incomplete segments, dry-run |
| `tests/jobs/test_review_paragraph_assembly.py` | Approved, rejected, skipped, missing package |
| `tests/core/status/test_paragraph_assembly_status.py` | Rollup: segments-only no longer complete; assembly pending/in-progress/blocked |
| `tests/fixtures/llm/review-paragraph-assembly/` | Mock approved/rejected responses |
| `tests/core/ports/test_artifact_ref.py` | New package ref kind |

Use `build_job_context(tmp_workspace)` with `models.provider: mock`.

## Architecture Doc Updates

Update as part of implementation:

- [cli-spec.md](../../../architecture/cli-spec.md) — split assemble vs review commands; add `package.json`; clarify `package-document` promotion
- [intermediate-artifacts.md](../../../architecture/preprocessing/intermediate-artifacts.md) — document `package.json` and two-command flow
- [editor-workflow.md](../../../architecture/preprocessing/editor-workflow.md) — assembly steps after segment completion
- `.cursor/skills/preprocessing-segments/SKILL.md` — note assembly is a separate explicit step after all segments complete

## Out of Scope

- `package-document` implementation
- `run preprocess` auto-advance to assembly
- New paragraph-level context note drafting (remains in `split-segments`)
- Reader app consumption of `content/` files
