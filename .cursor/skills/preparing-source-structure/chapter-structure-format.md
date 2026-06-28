# Chapter Structure Format

Interactive chapter splitting produces `chapter-proposal.json`. This file is the handoff point into automated paragraph preprocessing.

## Location

```text
preprocess/documents/<document-id>/
  normalized-document.json
  normalized-text.txt
  structure/
    chapter-proposal.json
    chapter-proposal.validation.json
```

## chapter-proposal.json

```json
{
  "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "model": "editor",
  "promptVersion": "editor-chapter-structure-v1",
  "inputHash": "sha256:...",
  "attempts": 1,
  "sourceHash": "sha256:...",
  "chapters": [
    {
      "id": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
      "title": "始計第一",
      "start": 0,
      "end": 842,
      "rationale": "Editor agreed: opens at chapter heading; closes before next heading."
    }
  ]
}
```

### Header fields

| Field | Value |
| --- | --- |
| `documentId` | UUID from registry / normalized manifest |
| `model` | Always `editor` for interactive proposals |
| `promptVersion` | Always `editor-chapter-structure-v1` |
| `attempts` | Always `1` unless the editor reruns a repair pass |
| `sourceHash` | Copy from `normalized-document.json` |
| `inputHash` | `sha256:` digest of the **normalized manifest hash string** (the full `normalizedHash` value, e.g. hash of `"sha256:abc..."` as UTF-8). Matches what downstream jobs expect for staleness checks. |

### Chapter items

| Field | Rules |
| --- | --- |
| `id` | UUID v4; stable across edits unless editor resets structure |
| `title` | Editor-approved chapter title |
| `start` | Character offset in `normalized-text.txt` (inclusive) |
| `end` | Character offset in `normalized-text.txt` (exclusive) |
| `rationale` | Brief note citing editor agreement or heading evidence |

Chapters must appear in ascending `start` order in the file.

## Span invariants (must pass before handoff)

Character offsets refer to `normalized-text.txt`. Let `L` = `characterCount` from the normalized manifest.

1. At least one chapter
2. First chapter `start` === 0
3. Last chapter `end` === `L`
4. For every chapter: `0 <= start < end <= L`
5. Chapters are contiguous: `chapters[i].end === chapters[i+1].start`
6. No overlap and no gaps

The agent should verify these before writing the proposal. Optionally confirm boundary text by reading `read_slice(start, min(start+80, end))` for each chapter — do not load the full document.

## chapter-proposal.validation.json

Written after span checks pass:

```json
{
  "status": "passed",
  "checks": []
}
```

Use `"status": "failed"` with `checks` entries only when recording a failed review pass the editor chose to keep on disk. Do not write a passed validation file for a proposal that fails invariants.

## Interactive process notes

### Finding offsets

For each proposed boundary at character position `P`:

1. Locate the boundary in context using slices around `P`
2. Confirm with the editor that `P` is the intended split point (usually a heading line start)
3. Record `P` as the next chapter's `start` (and previous chapter's `end`)

For heading lines, the split is typically at the **start of the heading line**, including any leading newline from the prior chapter's trailing content.

### Preamble and front matter

Text before the first recognized heading may become:

- Its own chapter (e.g. "序" / preface), or
- Part of the first chapter

Decide with the editor; record rationale.

### Revisions

| Change | Action |
| --- | --- |
| Title or rationale only | Edit item; keep `id` |
| Boundary moved | Update `start`/`end`; keep `id` if same logical chapter |
| Chapter merged or split | Assign new UUIDs for new units; remove dropped items |

After any boundary change, re-run span validation.

## Staleness

`chapter-proposal.json` is stale relative to normalization when:

- `sourceHash` ≠ current normalized manifest, or
- `inputHash` ≠ hash derived from current `normalizedHash`

If stale, warn the editor before running `split-paragraphs`. Boundaries may point at wrong text.

## Downstream handoff

When validation passes and the editor approves:

```shell
wenyan preprocess status <document-id>
wenyan preprocess split-paragraphs <document-id> --chapter <chapter-id>
```

Do not use a preprocessing CLI command for chapter structure — it is prepared interactively via this skill.
