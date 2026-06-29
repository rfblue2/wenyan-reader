---
name: drafting-context-notes
description: >-
  Draft segment-local context notes for a document segment identified by slug
  and chapter/paragraph/segment ordinals (same as preprocess show). Writes
  context-notes.json with web-grounded citations. Use when the editor asks to
  draft context notes, when run preprocess stops at context drafting, or for
  sunzi-bingfa ch1 p1 seg1 style requests.
---

# Drafting Context Notes

Replaces stubbed `annotate-segment-context`. The editor names a **document + location**; the agent does the rest.

## Editor input (minimal)

Provide any of:

| What | Example |
| --- | --- |
| Slug + ordinals | `sunzi-bingfa`, chapter **1**, paragraph **1**, segment **1** |
| Slug + segment UUID | `sunzi-bingfa`, segment `a7f3c891-…` |
| “Next” segment | gloss-approved, no `context-review.json` yet — document order |

You do **not** need to paste document UUIDs, artifact paths, JSON schemas, or skill instructions. This file is the instruction set.

## Agent workflow

```text
1. Resolve segment (show --json)
2. Confirm approved tokenization-review.json
3. Read tokenization, glosses, paragraph draft (duplication check)
4. Web-research factual claims
5. Write context-notes.json (model: editor)
6. uv run wenyan preprocess validate-artifacts <slug>
7. Summarize for editor; offer reviewing-context-notes
```

## Step 1 — Resolve segment (always use CLI)

**Ordinals (preferred — same as `preprocess show`):**

```shell
uv run wenyan preprocess show <slug> --chapter <n> --paragraph <n> --segment <n> --json
```

Example:

```shell
uv run wenyan preprocess show sunzi-bingfa --chapter 1 --paragraph 1 --segment 1 --json
```

From the JSON payload use `segmentId`, `documentId`, `text`, `tokens`, `grammarNotes`, `contextNotes`, `reviews`, `components`.

**Segment UUID only** (chapter/paragraph ordinals optional):

```shell
uv run wenyan preprocess show <slug> --segment <segment-uuid> --json
```

**Next gloss-ready segment** (no context review yet):

1. `uv run wenyan preprocess status <slug> --json` or inspect `components` on incomplete segments via `show`.
2. Pick the next segment in document order with approved gloss review (if glosses exist) and missing or non-approved context review.
3. Resolve with `show --json` using that segment’s ordinals or UUID.

Artifact directory after resolve:

`preprocess/documents/<documentId>/jobs/segments/<segmentId>/`

## Step 2 — Prerequisites

- `tokenization-review.json` exists with `status: "approved"`.
- If missing or rejected: stop and tell the editor to fix tokenization first.

Glosses and grammar are **not** required to draft context notes; read them when present for anchoring and duplication checks.

## Step 3 — Drafting rules

- Use web search for historical, biographical, or scholarly claims — not model memory alone.
- `contextNotes: []` when nothing beyond the segment text is needed (common for bare titles).
- Do not duplicate `paragraphContextNotes` from the paragraph draft.
- Factual or interpretive claims beyond the segment text need non-empty `sources`.

## Step 4 — Write `context-notes.json`

Path: `preprocess/documents/<documentId>/jobs/segments/<segmentId>/context-notes.json`

| Field | Value |
| --- | --- |
| `segmentId` | From `show` JSON |
| `model` | `"editor"` |
| `inputHash` | `sha256:` + hex digest of **raw bytes** of `tokenization-review.json` |
| `attempts` | `1` |
| `contextNotes` | Array of notes (may be empty) |

Compute `inputHash` the same way as the old annotate job, e.g.:

```shell
shasum -a 256 preprocess/documents/<documentId>/jobs/segments/<segmentId>/tokenization-review.json | awk '{print "sha256:" $1}'
```

**`ContextNoteItem`** (no `type` field):

```json
{
  "id": "<uuid-v4>",
  "anchorTokenIds": ["<token-id-from-tokenization>"],
  "body": "…",
  "sources": [
    {
      "label": "Short title",
      "excerpt": "Quoted supporting passage.",
      "url": "https://…",
      "accessedAt": "2026-06-28"
    }
  ]
}
```

| Citation field | When required |
| --- | --- |
| `label`, `excerpt` | When `sources` is non-empty |
| `url`, `accessedAt` | Optional (web sources) |

## Step 5 — Validate

```shell
uv run wenyan preprocess validate-artifacts <slug>
```

## Does not write

`context-review.json` — use [reviewing-context-notes](../reviewing-context-notes/SKILL.md).

## Agent constraints

- Never load full `normalized-text.txt` into context.
- Never ask the editor to restate this skill; ask only for missing location (slug/chapter/paragraph/segment) or approval of drafted notes.

## Example editor messages

These are sufficient on their own:

- `Draft context notes for sunzi-bingfa chapter 1 paragraph 1 segment 1.`
- `Context notes for sunzi-bingfa ch1 p2 seg1.`
- `Draft context for the next glossed segment in sunzi-bingfa.`

## Reference

- [reviewing-context-notes](../reviewing-context-notes/SKILL.md)
- [preprocessing-segments](../preprocessing-segments/SKILL.md)
- [source-grounding.md](../../../architecture/preprocessing/source-grounding.md)
