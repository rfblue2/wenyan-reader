# Context Notes Skills Design

## Summary

Replace CLI-driven context note generation with two interactive Cursor skills: one to draft `context-notes.json`, one to review and write `context-review.json`. Stub `annotate-segment-context` and `review-segment-context` so `run` stops with a pointer to the skills. Simplify source citations to inline objects on context notes only (no `sourceSnippets` on segment input). Remove unused `SegmentInput` fields. Split the shared `NoteItem` into separate grammar and context note types — grammar notes have no `sources` field.

Automated context annotation via remote LLM may return later (e.g. Anthropic with web search); skills and future CLI jobs must produce the same artifact shapes.

## Decisions

| Topic | Decision |
| --- | --- |
| Drafting | `.cursor/skills/drafting-context-notes/SKILL.md` — interactive agent with web access |
| Review | `.cursor/skills/reviewing-context-notes/SKILL.md` — separate skill; never edits notes |
| Context CLI | Stub with `not-implemented` + skill pointer (do not delete job modules yet) |
| `run preprocess` | Stop at pending context stage with skill pointer; eight-subjob completion unchanged |
| Segment input | Remove `sourceSnippets` and `candidateGlosses` from `SegmentInput` |
| Note types | `GrammarNoteItem` and `ContextNoteItem` — separate models, not a shared `NoteItem` |
| Note sources | `sources[]` only on `ContextNoteItem`; grammar notes have no sources field |
| Provenance | `model: "editor"` on skill-written context artifacts (same as `chapter-proposal.json`) |
| Future CLI | Same artifact schema so CLI and skills are interchangeable producers |
| Legacy data | None — greenfield; delete stale `preprocess/` artifacts rather than migrate |

## Note Types

Replace the shared `NoteItem` (`type`, `sources` on all notes) with two artifact-specific models:

**`GrammarNoteItem`** — used in `grammarNotes` only:

```json
{
  "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
  "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
  "body": "見 here is used in the sense of 'had an audience with' a superior."
}
```

No `type` field (array name is the discriminator). No `sources` field.

**`ContextNoteItem`** — used in `contextNotes` only:

```json
{
  "id": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
  "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
  "body": "Mencius is being introduced in an audience with a ruler.",
  "sources": [
    {
      "url": "https://example.com/mencius-1a1",
      "label": "Mencius 1A1",
      "excerpt": "孟子見梁惠王。",
      "accessedAt": "2026-06-28"
    }
  ]
}
```

No `type` field. `sources` defaults to `[]`.

Remove `NoteItem` from the public artifact models. Split `normalize_notes` into `normalize_grammar_notes` and `normalize_context_notes` (or equivalent) so grammar normalization never touches citations.

## Source Citation Shape

`NoteCitation` (context notes only) replaces `NoteSource` (`sourceId`, `label`, `detail`):

```json
{
  "url": "https://example.com/article",
  "label": "Shiji — biography of Sun Wu",
  "excerpt": "Quoted supporting passage from the source.",
  "accessedAt": "2026-06-28"
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `label` | When `sources` is non-empty | Short human-readable title |
| `excerpt` | When `sources` is non-empty | Supporting quoted text |
| `url` | Optional | Omit for offline references |
| `accessedAt` | Optional | ISO date; use for web sources when known |

- Each context note has `sources: []` or one or more `NoteCitation` objects.
- Multiple entries per note are allowed when several distinct citations support one note.
- No shared snippet registry; citations are not deduplicated across notes.

## Review Grounding

Update `SourceGroundingItem` to reference citations by position within a note:

```json
{
  "noteId": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
  "supported": true,
  "sourceIndexes": [0, 1]
}
```

Replace `sourceIds` with `sourceIndexes` (0-based into the note's `sources` array). Review skill populates this when verifying factual claims.

## Skill: Drafting Context Notes

**Path:** `.cursor/skills/drafting-context-notes/SKILL.md`

**Prerequisites:** Approved `tokenization-review.json` for the target segment.

**Reads:**

- `jobs/segments/<segment-id>/input.json`
- `tokenization.json`, `tokenization-review.json`
- Optional: `glosses.json`, paragraph `draft.json` (duplication check)

**Workflow:**

1. Inspect segment text and tokenization (use `wenyan preprocess show` when helpful).
2. Research as needed (web search, references) to ground factual or interpretive claims.
3. Draft `contextNotes` — use `[]` when no segment-local context is needed beyond the text.
4. Write `jobs/segments/<segment-id>/context-notes.json`.
5. Run `uv run wenyan preprocess validate-artifacts <slug>`.

**Artifact fields:**

| Field | Value |
| --- | --- |
| `segmentId` | Target segment UUID |
| `model` | `"editor"` |
| `inputHash` | `sha256(tokenization-review.json)` — same formula as former annotate job |
| `attempts` | `1` |
| `contextNotes` | Drafted notes |

**Drafting rules:**

- UUID v4 per note `id`.
- Non-empty `body` and valid `anchorTokenIds` (must exist in tokenization).
- Factual, historical, biographical, or interpretive claims beyond the segment text require non-empty `sources` with valid citations.
- Do not duplicate paragraph-level context notes from the paragraph draft.

**Does not write:** `context-review.json`.

## Skill: Reviewing Context Notes

**Path:** `.cursor/skills/reviewing-context-notes/SKILL.md`

**Prerequisites:** `context-notes.json` exists for the segment.

**Reads:** Context notes, tokenization, segment text; optional glosses and paragraph context notes.

**Workflow:**

1. Apply review checklist (usefulness, anchoring, grounding, gloss conflicts if glosses exist, no paragraph duplication).
2. Write `jobs/segments/<segment-id>/context-review.json` only — never edit `context-notes.json`.
3. On rejection: `status: "rejected"`, `findings` with `noteId` and reason; optional `sourceGrounding`.
4. On approval: `status: "approved"`, empty `findings`.
5. Run `validate-artifacts`.

**Artifact fields:**

| Field | Value |
| --- | --- |
| `segmentId` | Target segment UUID |
| `model` | `"editor"` |
| `inputHash` | `sha256(context-notes.json)` — same formula as former review job |
| `attempts` | `1` |
| `status` | `approved` or `rejected` |
| `findings` | Rejection details; empty when approved |
| `sourceGrounding` | Per-note citation verification when applicable |

**On rejection:** Editor fixes notes (re-run draft skill or hand-edit JSON), then re-run review skill.

## CLI and Pipeline Changes

### Stub context commands

`annotate-segment-context` and `review-segment-context`:

- Return non-zero exit with `not-implemented` (or equivalent existing pattern).
- Message names the appropriate skill path.

Keep job modules in place for a future CLI revival; implementation body becomes a stub.

### `run preprocess`

When the next pending subjob is `annotate-segment-context` or `review-segment-context`, stop with the skill pointer. Do not skip context stages. Segment completion still requires approved `context-review.json`.

### Grammar (unchanged CLI, schema update)

Keep `annotate-segment-grammar` and `review-segment-grammar` as LLM CLI jobs. LLM output schema uses `GrammarNoteItem` (no `sources`, no `type`). `normalize_grammar_notes` validates anchors only.

### Remove from segment input

Drop `sourceSnippets` and `candidateGlosses` from:

- `SegmentInput` model
- `split_segments` output (already empty)
- `gloss_segment` merge of `segment_input.candidate_glosses` (use glossary draft + prior segments only)
- Context job prompts and `source_snippet_ids` normalization path
- Architecture docs and examples

No migration path. This is a greenfield project — remove or regenerate `preprocess/` artifacts that use the old shapes (`NoteItem`, `sourceSnippets`, `candidateGlosses`, legacy `sources` on grammar notes) instead of transforming them in code.

## Documentation Updates

| File | Change |
| --- | --- |
| `.cursor/skills/preprocessing-segments/SKILL.md` | Context subjobs skill-driven; CLI stub behavior |
| `architecture/preprocessing/source-grounding.md` | Inline note citations; no segment-input snippets |
| `architecture/preprocessing/intermediate-artifacts.md` | `GrammarNoteItem` / `ContextNoteItem` / `NoteCitation`; `sourceIndexes`; segment input example |
| `architecture/storage-format.md` | Separate grammar vs context note shapes |
| `architecture/cli-spec.md` | Context commands stubbed; skills referenced |
| `AGENTS.md` | Point editors to context skills when annotating |

Prompt files `prompts/segment-context.md` and `prompts/segment-context-review.md` remain on disk but are unused until CLI revival.

## Testing

| Area | Change |
| --- | --- |
| Context job tests | Expect stub / `not-implemented` instead of LLM promotion |
| `normalize_grammar_notes` / `normalize_context_notes` | Anchor validation; context citation validation (label + excerpt when present) |
| Note models / review models | `GrammarNoteItem`, `ContextNoteItem`, `NoteCitation`; `sourceIndexes` on `SourceGroundingItem` |
| `gloss_segment` | No `candidateGlosses` from segment input |
| Fixtures | Update context note/review JSON examples |

## Error Handling

| Condition | Behavior |
| --- | --- |
| Context CLI invoked | `not-implemented` message → draft or review skill |
| `run` hits context stage without artifacts | Stop with skill pointer |
| Draft skill writes invalid JSON | `validate-artifacts` fails; editor fixes |
| Review rejects | `context-review.json` with findings; editor re-drafts |
| Missing tokenization review | Draft skill must not write notes until upstream approved |

## Out of Scope

- Multi-turn LLM tool loop / provider web search in CLI
- Review skill editing `context-notes.json` on reject
- Paragraph-level context note drafting (unchanged)
- Removing `model` from artifact schema (use `"editor"` instead)
- Backward compatibility with old artifact shapes

## Future: CLI Revival

When adding automated context annotation again:

1. Restore annotate/review job bodies (Anthropic or tool-enabled client).
2. Use the same `ContextNoteItem` / `NoteCitation` shape and `context-notes.json` / `context-review.json` layout.
3. Set `model` to the active LLM id instead of `"editor"`.
4. Skills remain valid for editorial override or segments that need manual research.
