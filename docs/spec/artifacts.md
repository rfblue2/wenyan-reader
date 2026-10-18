# Artifacts

> **Spec** — current on-disk preprocessing artifacts and status rules. Planned changes live in the [backlog](../backlog.md). Reader output: [Reader Package](reader-package.md). Pydantic models: `packages/wenyan-models/src/wenyan_models/artifacts/`.

Preprocessing artifacts live under `preprocess/documents/<document-id>/` and are committed to git. The reader never reads them. All models reject unknown fields (`extra="forbid"`), so the shapes below are exact.

## Layout

```text
preprocess/documents/<document-id>/
  normalized-document.json            ingest-document
  normalized-text.txt                 ingest-document
  structure/
    chapter-proposal.json             editor + agent skill
    chapter-proposal.validation.json  editor + agent skill
    chapters/<chapter-id>/
      paragraph-proposal.json         split-paragraphs
      paragraph-proposal.validation.json
  indexes/
    glossary-draft.json               review-segment-gloss (on approval)
  jobs/
    paragraphs/<paragraph-id>/
      draft.json                      split-segments
      validation.json
    segments/<segment-id>/
      input.json                      split-segments
      tokenization.json               tokenize-segment
      tokenization-review.json        review-segment-tokenization
      glosses.json                    gloss-segment
      gloss-review.json               review-segment-gloss
      grammar-notes.json              annotate-segment-grammar
      grammar-review.json             review-segment-grammar
      context-notes.json              drafting-context-notes skill
      context-review.json             reviewing-context-notes skill
    assembly/<paragraph-id>/
      package.json                    assemble-paragraph
      validation.json
    package/
      validation.json                 package-document
```

## Common fields

LLM- and editor-produced artifacts carry a metadata header:

| Field | Meaning |
|---|---|
| `model` | Active model id, `mock`, or `editor` for hand/skill-written artifacts. |
| `inputHash` | `sha256:` hash of the job's input (see below). Drives skip-on-rerun. |
| `attempts` | Always `1` today. |

Validation artifacts share `{status: "passed" | "failed", checks: [...]}`; assembly and package validations also carry `inputHash`. `status` is `passed` exactly when `checks` is empty; a file that disagrees fails to load.

### Input hashes

| Artifact | `inputHash` is sha256 of |
|---|---|
| `paragraph-proposal.json` | chapter text (also stored as `chapterTextHash`) |
| `draft.json` | paragraph text |
| `tokenization.json` | segment text |
| `glosses.json`, `grammar-notes.json`, `context-notes.json` | `tokenization-review.json` JSON |
| `*-review.json` | the reviewed draft's JSON |
| assembly `validation.json` | paragraph draft + per-segment hash of tokenization, glosses, grammar, and context outputs |
| package `validation.json` | normalized hash + glossary draft + assembly hashes |

## Effective status

Status is derived from files on disk at read time; there is no status database. Deleting an artifact rejects it.

| Unit | Rule |
|---|---|
| Draft component (tokenize, gloss, grammar, context) | `complete` if the file exists, else `pending`. |
| Review component | `pending` if the draft or review is missing; `complete` if `approved`; `blocked` if `rejected`. |
| Segment | `blocked` if any component is blocked; `complete` if all 8 are complete; `pending` if none; else `in-progress`. |
| Paragraph structure | `complete` if `draft.json` exists. |
| Paragraph assembly | `pending` until all segments complete or while outputs/validation are missing or failed; `stale` when the stored `inputHash` differs from the recomputed one; else `complete`. |
| Paragraph | `complete` only when assembly is complete; rolls up segments otherwise. |
| Chapter, document | Roll up children. `stale` counts as `pending`. |

Limits of the current rules:

- Only assembly detects staleness. Segment drafts and reviews are never `stale`, even if their inputs changed.
- `failed` is defined but never produced.
- Rerunning a draft job deletes its paired review, but does not cascade further (re-tokenizing leaves glosses and grammar `complete`).

## Writes

- Each file is written to `<name>.tmp` and renamed into place.
- Multi-file outputs (e.g. `split-segments`) write all temp files, then rename one at a time; a crash mid-rename can leave a partial set.
- LLM and parse failures write nothing. No raw responses or failure reports are kept.
- Status ignores `.tmp` files; nothing cleans them up.

## Shapes

### `normalized-document.json`

```json
{
  "documentId": "12ea50f2-…",
  "title": "孙子兵法",
  "sourceHash": "sha256:…",
  "normalizedHash": "sha256:…",
  "textPath": "normalized-text.txt",
  "characterCount": 7518,
  "textIndex": {"stride": 65536, "byteOffsets": [0]},
  "normalization": {"encoding": "utf-8", "punctuationPolicy": "preserve-source", "notes": []}
}
```

The text lives in the `normalized-text.txt` sidecar; `textIndex` maps character strides to byte offsets so jobs read only the spans they need.

### `chapter-proposal.json`

Written by the editor and agent ([preparing-source-structure](../../.opencode/skills/preparing-source-structure/SKILL.md)), not a CLI command.

```json
{
  "documentId": "…", "model": "editor", "inputHash": "sha256:…", "attempts": 1,
  "sourceHash": "sha256:…",
  "chapters": [{"id": "481af6b4-…", "title": "始計第一", "start": 0, "end": 448, "rationale": "…"}]
}
```

Offsets are character offsets into the normalized text.

### `paragraph-proposal.json`

```json
{
  "documentId": "…", "chapterId": "…", "model": "…", "inputHash": "sha256:…", "attempts": 1,
  "chapterTextHash": "sha256:…",
  "paragraphs": [{"id": "048109b3-…", "start": 0, "end": 6, "rationale": "…"}]
}
```

Offsets are relative to the chapter text. The sibling validation file records the span check.

### `jobs/paragraphs/<id>/draft.json`

```json
{
  "paragraphId": "…", "model": "…", "inputHash": "sha256:…", "attempts": 1,
  "segments": [{"id": "a7f3c891-…", "text": "始計第一"}],
  "paragraphContextNotes": [{"id": "…", "anchorSegmentIds": ["…"], "body": "…", "sources": []}],
  "draftRationale": {"segmentation": "…"}
}
```

Segment ids are minted by the model. `paragraphContextNotes` are optional and not validated; `sources` items may be strings or citation objects. The sibling `validation.json` is always `passed` with no checks.

### `jobs/segments/<id>/input.json`

```json
{"documentId": "…", "chapterId": "…", "paragraphId": "…", "segmentId": "…",
 "segmentText": "始計第一", "localContext": {}}
```

`localContext` is always empty. Gloss candidates are computed at job time, not stored here.

### `tokenization.json`

```json
{"segmentId": "…", "model": "…", "inputHash": "…", "attempts": 1,
 "text": "始計第一",
 "tokens": [{"id": "…", "surface": "始計", "start": 0, "end": 2}]}
```

Offsets index into `text`. Punctuation tokens are dropped after the model call, so tokens do not cover the full text.

### `glosses.json`

```json
{"segmentId": "…", "model": "…", "inputHash": "…", "attempts": 1,
 "glossDecisions": [{"tokenId": "…", "glossId": "7b3e8c2f-…", "decision": "create-new"}],
 "newGlossIds": ["7b3e8c2f-…"],
 "newGlosses": [{"id": "7b3e8c2f-…", "surface": "始計", "pinyin": "shǐjì", "gloss": "…"}]}
```

`decision` is `reuse-existing` or `create-new`. After the model call, decisions that hit a candidate id are rewritten to `reuse-existing` and duplicate new entries (same surface, pinyin, normalized gloss) are merged.

### `grammar-notes.json` / `context-notes.json`

```json
{"segmentId": "…", "model": "…", "inputHash": "…", "attempts": 1,
 "grammarNotes": [{"id": "…", "anchorTokenIds": ["…"], "body": "…"}]}
```

```json
{"segmentId": "…", "model": "editor", "inputHash": "…", "attempts": 1,
 "contextNotes": [{"id": "…", "anchorTokenIds": ["…"], "body": "…",
   "sources": [{"label": "…", "excerpt": "…", "url": "", "accessedAt": ""}]}]}
```

Grammar notes are normalized after the model call: notes with unknown anchors, empty bodies, or duplicate ids are dropped. Citation rules: [Quality Gates — Context notes](quality-gates.md#context-notes).

### `*-review.json`

```json
{"segmentId": "…", "model": "…", "inputHash": "…", "attempts": 1,
 "status": "approved", "findings": []}
```

`status` is `approved` or `rejected`. `findings` items are loose (`severity`, `message`, `tokenId`, `noteId`, `surface`, …; unknown keys ignored). `context-review.json` adds `sourceGrounding: [{noteId, supported, sourceIndexes}]`, where `sourceIndexes` are 0-based into the note's `sources`.

There is no separate blocked-report file: a rejected review is the blocked state, and status copies its findings into `requiredFixes`.

### `indexes/glossary-draft.json`

```json
{"glosses": [{"id": "…", "surface": "始計", "pinyin": "shǐjì", "gloss": "…"}]}
```

The document glossary under construction. `review-segment-gloss` merges a segment's new glosses on approval; `package-document` copies it to `glosses/index.json`. Entries are never removed.

### `jobs/assembly/<id>/package.json`

Same schema as the reader [paragraph file](reader-package.md#paragraph-file), with no metadata header. `validation.json` alongside: `{paragraphId, inputHash, status, checks}`.

### `jobs/package/validation.json`

`{inputHash, status, checks, paragraphsPackaged}`.
