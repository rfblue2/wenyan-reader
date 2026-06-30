---
name: reviewing-context-notes
description: >-
  Review segment context notes and write context-review.json. Target segments
  by document slug plus chapter/paragraph/segment ordinals (same as preprocess
  status --segment), or segment UUID. Use after drafting-context-notes or when the editor
  asks to review context notes for a segment.
---

# Reviewing Context Notes

Replaces stubbed `review-segment-context`. The editor names a **document + location**; the agent does the rest.

## Editor input (minimal)

| What | Example |
| --- | --- |
| Slug + ordinals | `sunzi-bingfa`, chapter **1**, paragraph **1**, segment **1** |
| Slug + segment UUID | `sunzi-bingfa`, segment `a7f3c891-…` |
| Review after draft | same location as the draft you just approved |

You do **not** need to paste schemas, hashes, or workflow steps.

**Prerequisite:** `context-notes.json` exists for that segment (from [drafting-context-notes](../drafting-context-notes/SKILL.md)).

## Agent workflow

```text
1. Resolve segment (status --segment --json)
2. Read context-notes.json and upstream artifacts
3. Apply review checklist
4. Write context-review.json only — never edit context-notes.json
5. validate-artifacts
6. Summarize (approved / rejected + findings)
```

## Step 1 — Resolve segment

```shell
uv run wenyan preprocess status <slug> --chapter <n> --paragraph <n> --segment <n> --json
```

Or `--segment <uuid>` without ordinals.

If `context-notes.json` is missing: stop and run drafting skill first.

## Step 2 — Review checklist

- Useful, correctly anchored to `anchorTokenIds`
- Factual claims have adequate `sources` (`label` + `excerpt`; `url` when web-based)
- Reject unsupported historical / literary / biographical claims
- No duplication of paragraph-level context notes
- If glosses exist: no conflict with gloss senses
- Approve `contextNotes: []` when appropriate

## Step 3 — Write `context-review.json`

Path: `preprocess/documents/<documentId>/jobs/segments/<segmentId>/context-review.json`

| Field | Value |
| --- | --- |
| `segmentId` | From segment |
| `model` | `"editor"` |
| `inputHash` | `sha256:` + hex digest of **raw bytes** of `context-notes.json` |
| `attempts` | `1` |
| `status` | `"approved"` or `"rejected"` |
| `findings` | `[]` if approved; else `{ "noteId", "reason" }` |
| `sourceGrounding` | Optional; `sourceIndexes` are 0-based into each note's `sources` |

On **reject**: editor re-runs drafting skill (or edits JSON), then this skill again.

## Step 4 — Validate

```shell
uv run wenyan preprocess validate-artifacts <slug>
```

## Example editor messages

- `Review context notes for sunzi-bingfa chapter 1 paragraph 1 segment 1.`
- `Review context for sunzi-bingfa ch1 p1 seg2.`

## Reference

- [drafting-context-notes](../drafting-context-notes/SKILL.md)
