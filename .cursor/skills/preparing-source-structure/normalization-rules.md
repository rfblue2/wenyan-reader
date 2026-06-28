# Normalization Rules

These rules define the canonical normalized text the preprocessing pipeline and reader depend on. The ingest job applies them deterministically; the agent enforces the same rules when reviewing or discussing normalization with the editor.

## Goal

Produce a stable UTF-8 text representation that:

- Preserves the Classical Chinese characters the reader will display
- Uses consistent line endings and document termination
- Can be referenced by character offsets in structure artifacts

Normalization is **not** an opportunity to modernize punctuation, simplify characters, or fix perceived source errors unless the editor explicitly opts in via `document.yaml`.

## Source layout

| File | Purpose |
| --- | --- |
| `sources/documents/<slug>/source.txt` | Raw full-document text (immutable working copy; edit only with editor approval) |
| `sources/documents/<slug>/document.yaml` | Ingest-time metadata and normalization policy |
| `sources/registry.yaml` | Slug, title, status, optional `documentId` |

The source is always one complete document, not a chapter excerpt.

## Normalization transforms (deterministic)

Applied in order during ingest:

1. **Encoding**: Read as UTF-8.
2. **Line endings**: Replace `\r\n` and lone `\r` with `\n`.
3. **Trailing newline**: Ensure the file ends with exactly one `\n`.

No other transforms in the default policy.

## document.yaml

```yaml
title: 孙子兵法
language: zh-Hant
script: traditional
provenance: local
normalization:
  encoding: utf-8
  punctuationPolicy: preserve-source
sourceHeadings:
  pattern: chapter-title
  examples:
    - 始計第一
    - 作戰第二
```

| Field | Meaning |
| --- | --- |
| `title` | Display title; copied to normalized manifest |
| `language` / `script` | Editorial metadata for grounding (optional) |
| `provenance` | Source origin note (optional) |
| `normalization.encoding` | Must be `utf-8` |
| `normalization.punctuationPolicy` | Default `preserve-source` — do not alter punctuation |
| `normalization.notes` | Optional list of editor-agreed exceptions (add when policy deviates) |
| `sourceHeadings` | Hints for interactive chapter work — **not** automatic structure |

## Output artifacts

After `wenyan preprocess ingest-document sources/documents/<slug>`:

### normalized-document.json (manifest)

Metadata only — no embedded full text.

```json
{
  "documentId": "<uuid>",
  "title": "孙子兵法",
  "sourceHash": "sha256:<hex>",
  "normalizedHash": "sha256:<hex>",
  "textPath": "normalized-text.txt",
  "characterCount": 12345,
  "textIndex": {
    "stride": 65536,
    "byteOffsets": [0]
  },
  "normalization": {
    "encoding": "utf-8",
    "punctuationPolicy": "preserve-source",
    "notes": []
  }
}
```

- `sourceHash`: SHA-256 of raw `source.txt` bytes
- `normalizedHash`: SHA-256 of `normalized-text.txt` bytes
- `characterCount`: Unicode code point count of normalized text
- `textIndex`: Byte-offset index for slice reads — produced by ingest; do not hand-edit

### normalized-text.txt (sidecar)

The canonical normalized full document. All chapter `start`/`end` offsets in structure artifacts refer to **character positions in this file** (0-based, end exclusive).

## Agent review checklist

When reviewing normalization with the editor:

- [ ] First and last ~500 characters look correct
- [ ] Sample around any known heading matches editor expectations
- [ ] No `\r` characters remain
- [ ] File ends with a single newline
- [ ] Character count in manifest is plausible for source size
- [ ] Hashes change after `--force` re-ingest when source changed

## When to re-ingest

Re-run `wenyan preprocess ingest-document ... --force` when:

- `source.txt` changed
- Normalization policy in `document.yaml` changed

Re-ingest **invalidates** downstream structure artifacts that depend on `normalizedHash`. Warn the editor before re-ingesting a document that already has chapter or paragraph proposals.

## What normalization does not do

- Split chapters (interactive step — see SKILL.md)
- Strip commentary or parallel text
- Convert traditional ↔ simplified characters
- Normalize full-width / half-width punctuation
- Remove blank lines (blank lines are preserved)

If the editor needs any of these, record the policy in `document.yaml` `normalization.notes` and agree on whether ingest rules must change (separate engineering task).
