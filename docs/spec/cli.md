# CLI

> **Spec** — current behavior of `wenyan preprocess`. Planned changes live in the [backlog](../backlog.md). Artifact shapes and status rules: [Artifacts](artifacts.md).

The CLI is the editor's control surface for preprocessing. Every command runs from the repo root:

```shell
uv run wenyan preprocess <command> [args]
```

## Commands

| Command | Scope | Writes | LLM | State |
|---|---|---|---|---|
| `ingest-document <source-dir>` | document | `normalized-document.json`, `normalized-text.txt`, `sources/registry.yaml` id | no | implemented |
| `split-paragraphs --chapter` | chapter | `paragraph-proposal.json` + `.validation.json` | yes | implemented |
| `split-segments --paragraph` | paragraph | `draft.json`, `validation.json`, `segments/*/input.json` | yes | implemented |
| `review-paragraph-structure --paragraph` | paragraph | — | — | stub (exit 2) |
| `tokenize-segment --segment\|--paragraph` | segment / batch | `tokenization.json` | yes | implemented |
| `review-segment-tokenization --segment\|--paragraph` | segment / batch | `tokenization-review.json` | yes | implemented |
| `gloss-segment --segment\|--paragraph` | segment / batch | `glosses.json` | yes | implemented |
| `review-segment-gloss --segment\|--paragraph` | segment / batch | `gloss-review.json`; merges into `indexes/glossary-draft.json` on approval | yes | implemented |
| `annotate-segment-grammar --segment\|--paragraph` | segment / batch | `grammar-notes.json` | yes | implemented |
| `review-segment-grammar --segment\|--paragraph` | segment / batch | `grammar-review.json` | yes | implemented |
| `annotate-segment-context --segment\|--paragraph` | segment | — | — | stub (exit 1); use [drafting-context-notes](../../.opencode/skills/drafting-context-notes/SKILL.md) |
| `review-segment-context --segment\|--paragraph` | segment | — | — | stub (exit 1); use [reviewing-context-notes](../../.opencode/skills/reviewing-context-notes/SKILL.md) |
| `assemble-paragraph --paragraph` | paragraph | `jobs/assembly/<id>/package.json` + `validation.json` | no | implemented |
| `package-document` | document | `content/documents/<id>/**`, `jobs/package/validation.json` | no | implemented |
| `run` | segment / paragraph | whatever the chained jobs write | yes | implemented |
| `status` | any | — | no | implemented |
| `validate-artifacts` | any | — | no | partial |
| `prune` | document | deletes orphaned dirs | no | implemented |
| `review-report --segment` | segment | — | — | stub (exit 2); use `status --segment` |

Preprocess paths are relative to `preprocess/documents/<document-id>/`. Chapter structure has no command; it is written interactively with the [preparing-source-structure](../../.opencode/skills/preparing-source-structure/SKILL.md) skill.

## Common behavior

### Arguments

- `<document>`: document UUID or source slug (resolved via `sources/registry.yaml`).
- `--chapter`: UUID, 1-based number, title, or unique title prefix.
- `--paragraph`: UUID, or number when `--chapter` is set.
- `--segment`: UUID, or number when `--paragraph` is set (and `--chapter` when the paragraph is a number).

On segment-batch commands, `--segment` selects one segment; `--paragraph` alone runs every segment in that paragraph's draft. Other commands use `--chapter`/`--paragraph` only to resolve numbers.

UUIDs given for `--paragraph` (without `--chapter`) and `--segment` are not checked for existence.

### Options

| Option | Commands | Behavior |
|---|---|---|
| `--force` | artifact-producing commands | Rerun even when the stored `inputHash` matches. |
| `--dry-run` | artifact-producing commands, `prune` | Run the job but write nothing. LLM jobs still call the model. |
| `--json` | all except stubs | Machine-readable output (see below). |

### Rerun and writes

- A job **skips** when its existing artifact's `inputHash` equals the freshly computed one (assembly and package also require a passed validation). Hash definitions: [Artifacts — Input hashes](artifacts.md#input-hashes).
- Each artifact is written to `<name>.tmp`, then renamed into place. Multi-file outputs write every temp file before renaming any.
- An LLM or parse failure writes nothing.
- Rewriting a segment draft (tokenization, glosses, grammar) deletes its paired review.
- Batch runs stop at the first failing segment.

### Output and exit codes

Job commands print `complete`, the skip reason, or the failure message. With `--json`:

```json
{"outcome": {"kind": "promoted", "artifact": { … }}}
{"outcome": {"kind": "skipped", "reason": "…"}}
{"outcome": {"kind": "failure", "code": "blocked-upstream", "message": "…"}}
```

| Exit | Meaning |
|---|---|
| 0 | Promoted or skipped. |
| 1 | Job failure: review rejected, validation failed, `blocked-upstream`, `nothing-to-package`, context stubs; also `validate-artifacts` issues and unresolved refs in `status`/`validate-artifacts`. |
| 2 | Usage error: bad unit ref on job commands; `review-paragraph-structure` and `review-report` stubs. |

Uncaught LLM HTTP or parse errors (after client retries) exit with a traceback.

## Command notes

### `ingest-document`

Takes a directory under `sources/documents/<slug>/`. Assigns a document UUID (saved to `sources/registry.yaml`), streams the source into `normalized-text.txt`, and writes `normalized-document.json`. Skips when the manifest already exists.

### `split-paragraphs`

Sends the full chapter text to the model, which proposes paragraph spans. Spans are validated for contiguous, non-overlapping coverage of the chapter. On failure nothing is written.

### `split-segments`

Sends one paragraph to the model, which proposes segment texts and optional paragraph-level context notes. Writes the draft, a validation artifact (currently always `passed` with no checks), and one `input.json` per segment.

### Segment jobs

Order within a segment: tokenize → review tokenization → gloss and grammar (each requires an approved tokenization review) → their reviews → context notes → context review. A rejected review writes the review artifact and exits 1; the component shows `blocked`.

### `assemble-paragraph`

Requires `draft.json` and all eight components complete for every segment. Compiles the reader paragraph shape, validates it, and writes `package.json` + `validation.json`. On failure writes only a failed `validation.json`. Not run by `run`.

### `package-document`

Promotes every paragraph whose assembly validation passed and is current to `content/documents/<document-id>/`, builds `document.json` (chapters with at least one packaged paragraph), `chapter.json` files, and copies the glossary draft to `glosses/index.json`. Writes `jobs/package/validation.json`. Fails with `nothing-to-package` when no paragraph is ready.

### `run`

| Form | Behavior |
|---|---|
| `run <doc>` / `--next-segment` | Pick the first incomplete segment (running `split-segments` first if the next paragraph has no draft) and run its eight components in order. |
| `--segment <ref>` | Same, for one segment. |
| `--next-paragraph` | Run `split-segments` for the first paragraph without a draft. |

Stops at the first failure. Because context jobs are stubs, a segment without hand-written context artifacts always stops at `annotate-segment-context`. Never runs `split-paragraphs`, `assemble-paragraph`, or `package-document`.

### `status`

Lists the next level down: document → chapters, chapter → paragraphs, paragraph → segments (plus `assembly`). Segment scope renders the segment text, a token/gloss table, notes, review findings, and the eight components; `--json` returns a `SegmentShowView`. Status rules: [Artifacts — Effective status](artifacts.md#effective-status).

Paragraph payload (abridged, from `sunzi-bingfa`):

```json
{
  "documentId": "12ea50f2-…",
  "chapterId": "481af6b4-…",
  "paragraphId": "048109b3-…",
  "scope": {"type": "paragraph"},
  "structure": {"status": "complete", "segmentCount": 1},
  "counts": {"chapters": null, "paragraphs": null, "segments": 1,
             "complete": 1, "inProgress": 0, "pending": 0, "failed": 0, "blocked": 0},
  "segments": [
    {"segmentId": "a7f3c891-…", "ordinal": 1, "status": "complete", "textPreview": "始計第一",
     "progress": {"componentsComplete": 8, "componentsTotal": 8}, "blockedComponent": null}
  ],
  "assembly": {"kind": "assemble-paragraph", "status": "complete", "artifactPath": "…/package.json",
               "attempts": null, "blockedReason": null, "requiredFixes": []}
}
```

Document and chapter payloads have the same `counts` shape and list `chapters[]` (`progress.paragraphsComplete/Total`) or `paragraphs[]` (`progress.segmentsComplete/Total`). Component items (`ComponentStatusItem`) carry `kind`, `status`, `artifactPath`, `attempts`, `blockedReason`, and `requiredFixes` (copied from review findings).

### `validate-artifacts`

At every scope, checks only that `normalized-document.json` and its text sidecar exist and that the sidecar hash matches. Prints `ok`/`invalid`, or `{"issues": [{code, message, ref}]}` with `--json`.

### `prune`

Deletes `jobs/segments/<id>/` directories not listed in any current paragraph draft, and stale `jobs/assembly/<id>/` directories. Only removed segments are reported. `--dry-run` reports without deleting.
