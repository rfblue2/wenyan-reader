# Grammar and Context Notes Design

## Summary

Implement the four stubbed segment subjobs for grammar and context notes: `annotate-segment-grammar`, `review-segment-grammar`, `annotate-segment-context`, and `review-segment-context`. Wire them into `run preprocess` so a segment can complete all eight subjobs. Defer paragraph assembly, `show`, reader packaging, and `introKey`.

## Decisions

| Topic | Decision |
| --- | --- |
| Scope | Segment subjobs only (four annotate/review jobs + models, prompts, tests, `run preprocess` wiring) |
| Empty segments | `grammarNotes: []` / `contextNotes: []` when nothing salient applies |
| Upstream for drafting | Approved tokenization review only; `inputHash` derived from tokenization review JSON |
| Gloss dependency | Optional at review time — pass glosses when present; grammar review checks gloss conflicts only when glosses exist |
| `introKey` | Dropped from draft note shape — not used by reader or pipeline today |
| Implementation style | Mirror gloss jobs (four modules + small shared `normalize_notes()` helper) |
| Review failure | Fail-fast — write review artifact, non-zero exit, block only that subjob |
| Test backend | Mock LLM fixtures; no live LLM required in CI |

## Note Shape

Notes in draft artifacts use a typed `NoteItem` model:

```json
{
  "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
  "type": "grammar",
  "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
  "body": "見 here is used in the sense of 'had an audience with' a superior.",
  "sources": []
}
```

```json
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
```

Required fields per note:

- `id` — UUID v4
- `type` — `"grammar"` or `"context"`
- `anchorTokenIds` — non-empty when the note is retained
- `body` — non-empty when the note is retained

Optional fields:

- `sources` — citations for context notes with factual or interpretive claims

Grammar notes omit `sources` unless the model includes them; context review enforces grounding when claims need support and `sourceSnippets` were available in segment input.

## Artifact Models

Add to `packages/wenyan-models/src/wenyan_models/artifacts/segment.py`:

| Model | Artifact file | Key fields |
| --- | --- | --- |
| `NoteItem` | (shared) | `id`, `type`, `anchorTokenIds`, `body`, `sources` |
| `NoteSource` | (shared) | `sourceId`, `label`, `detail` |
| `GrammarNotesArtifact` | `grammar-notes.json` | `segmentId`, `model`, `inputHash`, `attempts`, `grammarNotes` |
| `GrammarReviewArtifact` | `grammar-review.json` | `segmentId`, `model`, `inputHash`, `attempts`, `status`, `findings` |
| `ContextNotesArtifact` | `context-notes.json` | `segmentId`, `model`, `inputHash`, `attempts`, `contextNotes` |
| `ContextReviewArtifact` | `context-review.json` | `segmentId`, `model`, `inputHash`, `attempts`, `status`, `findings`, `sourceGrounding` |

`sourceGrounding` on context review follows the intermediate-artifacts pattern:

```json
{
  "noteId": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
  "supported": true,
  "sourceIds": ["src-001"]
}
```

Artifact headers (`model`, `inputHash`, `attempts`) match existing segment subjob conventions.

## Job Behavior

### Upstream prerequisites

| Job | Requires |
| --- | --- |
| `annotate-segment-grammar` | `input.json`, `tokenization.json`, approved `tokenization-review.json` |
| `review-segment-grammar` | `grammar-notes.json`, `input.json`, `tokenization.json`; `glosses.json` if present |
| `annotate-segment-context` | same as grammar annotate |
| `review-segment-context` | `context-notes.json`, `input.json`, `tokenization.json`; `glosses.json` if present |

Drafting does **not** wait for gloss review. The existing `SEGMENT_SUBJOBS` order still runs grammar and context after gloss in `run preprocess`, but each job's prerequisite check is tokenization review only so manual CLI invocation can fan out after tokenization review when desired.

### Staleness and skip

- `inputHash` = SHA-256 of approved tokenization review JSON (same pattern as `gloss_segment.py`).
- Skip when artifact exists, `inputHash` matches, and `--force` is not set.

### Deterministic post-processing

Add `src/wenyan/core/notes/normalize_notes.py` with `normalize_notes(notes, tokenization, *, source_snippet_ids)`:

- Drop notes with empty `body` or empty `anchorTokenIds`.
- Ensure every `anchorTokenId` references a token in the tokenization.
- Ensure note `id` values are unique within the artifact.
- For context notes with `sources`, validate each `sourceId` against segment input `sourceSnippets` when IDs are present; drop invalid source references or reject via validation (drop invalid references, keep note if body and anchors are valid).

Grammar and context drafting jobs call this after the LLM response and before promotion.

### Review jobs

Follow `review_segment_gloss.py`:

- Load draft artifact and compute `inputHash` from draft JSON.
- Build prompt context with segment text, tokenization, draft notes, and optional glosses.
- Context review also passes `sourceSnippets` and paragraph-level `paragraphContextNotes` from paragraph draft when available (for duplication check).
- Write review artifact; return `JobFailure` with `review-rejected` on rejection.

### CLI and run wiring

| File | Change |
| --- | --- |
| `src/wenyan/jobs/annotate_segment_grammar.py` | New |
| `src/wenyan/jobs/review_segment_grammar.py` | New |
| `src/wenyan/jobs/annotate_segment_context.py` | New |
| `src/wenyan/jobs/review_segment_context.py` | New |
| `src/wenyan/jobs/run_preprocess.py` | Register all four in `_IMPLEMENTED_SUBJOBS` |
| `src/wenyan/core/run/segment_pipeline.py` | Add grammar/context review models to `_REVIEW_MODEL` |
| `src/wenyan/cli/preprocess.py` | Replace stubs with real handlers |

CLI targets match gloss: `--segment` or `--paragraph` batch for annotate jobs; `--segment` only for review jobs.

## Prompts

Add under `prompts/`:

| Template | Purpose |
| --- | --- |
| `segment-grammar.md` | Draft grammar notes anchored to tokens; return empty array when none apply |
| `segment-grammar-review.md` | Check constructions present, anchors correct, useful not generic; gloss conflict when glosses provided |
| `segment-context.md` | Draft context notes; cite `sourceId` for factual claims; empty array when none apply |
| `segment-context-review.md` | Usefulness, anchoring, source grounding, no duplication of paragraph-level notes |

Prompt style follows `segment-gloss.md`: task description, rules, output schema reference, templated context variables (`segment_text`, `tokenization_json`, `input_hash`, etc.).

### Grammar drafting rules (prompt content)

- Explain salient Classical Chinese constructions in the segment.
- Anchor each note to one or more token IDs from the tokenization.
- Write for an English-speaking learner; avoid generic textbook filler.
- Return `grammarNotes: []` when the segment has no construction worth calling out.

### Context drafting rules (prompt content)

- Explain people, places, historical setting, literary references, or interpretive context needed for comprehension.
- Anchor each note to relevant token IDs.
- Cite `sourceId` from provided `sourceSnippets` when making factual or interpretive claims.
- Return `contextNotes: []` when no context beyond the segment text itself is needed.

## Testing

| Area | Coverage |
| --- | --- |
| `tests/jobs/test_annotate_segment_grammar.py` | Happy path, skip on current hash, missing upstream, dry-run |
| `tests/jobs/test_review_segment_grammar.py` | Approved and rejected review |
| `tests/jobs/test_annotate_segment_context.py` | Same patterns as grammar |
| `tests/jobs/test_review_segment_context.py` | Approved, rejected, source grounding findings |
| `tests/core/notes/test_normalize_notes.py` | Anchor validation, dedup, empty note stripping |
| `tests/fixtures/llm/` | Mock responses for all four jobs |
| `tests/prompts/test_prompt_templates.py` | Register new templates and context keys |
| `tests/core/run/test_work_queue.py` | `run preprocess` advances through all eight subjobs |

Tests use `build_job_context(tmp_workspace)` with `models.provider: mock`.

## Out of Scope

- `assemble-paragraph` note merging into final paragraph package
- `show` command note display
- `introKey` field (drop until a consumer exists)
- Paragraph-level context note drafting (remains in paragraph structure job)
- Deterministic segment-output validation during assembly
- Storage format doc update for `introKey` removal (follow-up when reader packaging is implemented)

## Architecture Doc Updates

Update these files as part of implementation:

- `architecture/preprocessing/intermediate-artifacts.md` — note examples without `introKey`; typed note fields in grammar/context artifacts
- `.cursor/skills/preprocessing-segments/SKILL.md` — mark grammar/context subjobs as implemented

## Error Handling

| Condition | Behavior |
| --- | --- |
| Missing tokenization or unapproved tokenization review | `JobFailure` `missing-input` or `blocked-upstream` |
| LLM returns malformed JSON | Non-zero exit via existing `complete_model` parser |
| Review rejection | Write review artifact with `status: rejected`, `JobFailure` `review-rejected` |
| `--dry-run` | Return promoted artifact without writing |

## Follow-up (after this slice)

- `assemble-paragraph` merging notes into `segments[].notes`
- `show` command grammar/context display
- Revisit `introKey` if reader needs cross-segment introduction tracking
- Deterministic segment-output validation for note anchors during assembly
