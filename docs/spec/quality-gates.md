# Quality Gates

> **Spec** — the deterministic checks and review passes that gate content today, and how failures block work. Planned checks live in the [backlog](../backlog.md).

Two kinds of gate:

- **Deterministic checks** in code prove structure: spans, ids, anchors, gloss references.
- **Reviews** judge editorial content: token boundaries, gloss sense, pinyin, grammar accuracy, source support. LLM reviews run as separate jobs after drafting; context review is done by editor + agent.

## Deterministic checks

| Gate | When | Checks | Output |
|---|---|---|---|
| Paragraph spans | `split-paragraphs` | Spans (after sorting) are contiguous, non-overlapping, and cover the chapter. Failure writes nothing. | `paragraph-proposal.validation.json` |
| Gloss and grammar prerequisites | `gloss-segment`, `annotate-segment-grammar` | Tokenization review is approved, else `blocked-upstream`. | — |
| Draft cleanup | after each LLM draft | Drop punctuation tokens; rewrite candidate gloss hits to `reuse-existing` and merge duplicate new glosses; drop grammar notes with bad anchors, empty bodies, or duplicate ids. | — |
| Paragraph assembly | `assemble-paragraph` | See [Reader Package — Validation](reader-package.md#validation). | `jobs/assembly/<id>/validation.json` |
| Document package | `package-document` | See [Reader Package — Validation](reader-package.md#validation). | `jobs/package/validation.json` |
| Normalized document | `validate-artifacts` | Manifest and sidecar exist; sidecar hash matches. | stdout |

The chapter proposal validation file is written by the editor + agent, not code. `split-segments` writes a `passed` validation without running checks.

## Reviews

Every review writes `*-review.json` with `approved` or `rejected` and `findings`. Checklists live in the prompts and skills; the essentials:

### Tokenization (`review-segment-tokenization`)

Input: the tokenization artifact.

- No punctuation- or whitespace-only tokens.
- Not too coarse: split phrases across particles (`國/之/大事`, not `國之大事`).
- Not too fine: keep names, titles, places, and fixed compounds whole (`孫子`, `大事`, `死生`, `存亡`).
- No overlaps, wrong surfaces, bad offsets, or missing glossable characters.

### Gloss (`review-segment-gloss`)

Input: segment text, tokenization, glosses, candidate glosses.

- Exactly one decision per token.
- Correct sense in context; pinyin (with tone) matches that sense, not a default reading — e.g. `將` is `jiàng` "general" in `四曰將`, `jiāng` "will" in `將聽吾計`.
- No `create-new` that duplicates a candidate.

On approval, merges new glosses into `indexes/glossary-draft.json`.

### Grammar (`review-segment-grammar`)

Input: segment text, tokenization, grammar notes, glosses (if present).

- Notes describe constructions actually present, anchored to the right tokens.
- Useful, not generic filler; no conflict with selected gloss senses.
- An empty note list is acceptable.

### Context notes

Drafted with [drafting-context-notes](../../.opencode/skills/drafting-context-notes/SKILL.md) and reviewed with [reviewing-context-notes](../../.opencode/skills/reviewing-context-notes/SKILL.md). Requires an approved tokenization review.

Drafting rules:

- Research historical, biographical, and scholarly claims on the web; do not rely on model memory.
- Claims beyond the segment text need `sources`; each citation has `label` and `excerpt`, optional `url` and `accessedAt`. If no source supports a claim, omit the note.
- Write `contextNotes: []` when nothing is needed (common for titles).
- Do not duplicate paragraph-level context notes. Grammar notes never carry sources.

Review checklist: anchored correctly; factual claims cited; no unsupported historical, literary, or biographical claims; no duplication; no conflict with glosses. The review may record `sourceGrounding` per note with `sourceIndexes` into its `sources`.

## Blocking

- A rejected review blocks only that component. Status shows it `blocked` with the findings as `requiredFixes`.
- A blocked tokenization review makes gloss and grammar fail `blocked-upstream`.
- A blocked segment leaves sibling segments usable but prevents its paragraph from assembling, and so from packaging.
- To unblock: rerun the draft (which deletes the paired review), edit the artifact, or delete it, then rerun the review.

There is no retry counter: a component is blocked only by a rejected review, never by repeated failures.
