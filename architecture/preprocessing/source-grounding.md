# Source Grounding

## Purpose

Context notes that make factual or interpretive claims beyond the segment text should cite inline sources. Grammar notes do not use sources.

## Context note citations

Each `ContextNoteItem` may include a `sources` array of self-contained citation objects:

| Field | Required | Notes |
| --- | --- | --- |
| `label` | When `sources` non-empty | Short title |
| `excerpt` | When `sources` non-empty | Supporting quoted text |
| `url` | Optional | Web reference |
| `accessedAt` | Optional | ISO date for web sources |

There is no shared snippet registry on segment input. The [drafting-context-notes](../../.cursor/skills/drafting-context-notes/SKILL.md) skill researches and writes citations during interactive preprocessing.

If no source supports a claim, omit the note or reject it in [reviewing-context-notes](../../.cursor/skills/reviewing-context-notes/SKILL.md) rather than inventing a citation.

## Review handoff

Context review records `sourceGrounding` with `sourceIndexes` (0-based into each note's `sources` array) when verifying citations.

See [Review And Quality Jobs](review-and-quality-jobs.md) for validation and blocking behavior.
