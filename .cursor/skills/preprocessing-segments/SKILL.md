---
name: preprocessing-segments
description: >-
  Guides an editor or agent through resumable segment preprocessing after chapter
  structure exists. Use when running split-paragraphs, split-segments, segment
  tokenization, gloss, grammar, context subjobs, reviewing artifacts, continuing
  with the next segment, or when an editor asks the agent to preprocess content
  with the real LLM backend.
---

# Preprocessing Segments

Segment preprocessing is **mechanical and CLI-driven** once `structure/chapter-proposal.json` is validated. The editor chooses when to advance; the agent runs commands, inspects artifacts, and reports blocked units.

Prerequisite: complete [preparing-source-structure](../preparing-source-structure/SKILL.md) through validated chapter structure.

## When to use this skill

- Starting paragraph/segment structure for a chapter
- Resuming after an interrupted run
- Processing the next segment in document order
- Preparing segment inputs for a new paragraph (`split-segments`)
- Running live LLM preprocessing (MiniMax or Anthropic) when the editor requests it
- Diagnosing blocked review artifacts or stale downstream files

## Roles

| Role | Responsibility |
| --- | --- |
| **Editor (user)** | Chooses scope, approves boundaries, decides when to `--force` a rerun |
| **Agent** | Run CLI commands, read status/artifacts, explain failures, never load full `normalized-text.txt` |

## Segment completion

A segment is **finished** when all eight subjobs have approved review artifacts:

1. `tokenize-segment` → `review-segment-tokenization`
2. `gloss-segment` → `review-segment-gloss`
3. `annotate-segment-grammar` → `review-segment-grammar` (CLI)
4. [drafting-context-notes](../drafting-context-notes/SKILL.md) → [reviewing-context-notes](../reviewing-context-notes/SKILL.md)

## Slice scope (current implementation)

| Subjob | Status |
| --- | --- |
| `split-paragraphs`, `split-segments` | Implemented |
| `tokenize-segment`, `review-segment-tokenization` | Implemented |
| `gloss-segment`, `review-segment-gloss` | Implemented |
| `annotate-segment-grammar`, `review-segment-grammar` | Implemented (CLI) |
| `annotate-segment-context`, `review-segment-context` | Stubbed — use context skills |
| `show` | Implemented |
| `prune` | Implemented |
| `run` | Chains all subjobs through context review; stops with `not-implemented` at assembly |

## LLM backend

Configuration resolves from `.env` → `config/preprocessing.yaml`. Run from repo root:

```shell
uv run wenyan preprocess ...
```

## Resume workflow

```text
- [ ] 1. Chapter structure validated
- [ ] 2. Paragraph proposal for target chapter
- [ ] 3. Segment drafts for target paragraph(s)
- [ ] 4. Each segment fully preprocessed (all subjobs + reviews)
- [ ] 5. Editor inspected artifacts; advance or repair
```

### Inspect before running

```shell
uv run wenyan preprocess status <slug> --json
uv run wenyan preprocess validate-artifacts <slug>
uv run wenyan preprocess prune <slug> --dry-run
```

### Inspect segment outputs (glosses, reviews)

```shell
uv run wenyan preprocess status <slug> --chapter 1 --paragraph 1 --segment 1
uv run wenyan preprocess status <slug> --segment <segment-uuid> --json
```

Use ordinals with `--chapter` / `--paragraph` as needed, or pass a segment UUID directly.

### Shorthand: finish the next segment

```shell
uv run wenyan preprocess run <slug>
```

Equivalent to `--next-segment`. Finds the next incomplete segment in document order, runs `split-segments` first if that paragraph lacks a draft, then runs every pending subjob for the segment. Repeats until the segment is fully complete or a step fails.

Repeat until the command prints `no segments pending preprocessing`.

### Shorthand: prepare the next paragraph's segments

When paragraph boundaries exist but segment `input.json` files are missing:

```shell
uv run wenyan preprocess run <slug> --next-paragraph
```

### Explicit segment

```shell
uv run wenyan preprocess run <slug> --segment <segment-id>
```

### Focused commands (same jobs, no chaining)

```shell
uv run wenyan preprocess split-paragraphs <slug> --chapter <chapter-id>
uv run wenyan preprocess split-segments <slug> --paragraph <paragraph-id>
uv run wenyan preprocess tokenize-segment <slug> --segment <segment-id>
uv run wenyan preprocess review-segment-tokenization <slug> --segment <segment-id>
```

## Handling failures

### `not-implemented` from context CLI or `run`

Context annotate/review commands are stubbed. When `run` reaches context stages it stops with a pointer to:

- [drafting-context-notes](../drafting-context-notes/SKILL.md) for `context-notes.json`
- [reviewing-context-notes](../reviewing-context-notes/SKILL.md) for `context-review.json`

The editor only names slug + chapter/paragraph/segment ordinals (e.g. “Draft context notes for sunzi-bingfa chapter 1 paragraph 1 segment 1”). The skill resolves the segment via `preprocess status --segment --json`.

Grammar and upstream subjobs may still be complete; use the skills to finish the segment.

### `not-implemented` from other `run` stages

### Review rejected

Read the relevant `*-review.json` under `jobs/segments/<segment-id>/`. Rerun the draft command with `--force`, then the review command.

### Editor rejects generated output

Delete the artifact they dislike, then rerun:

```shell
uv run wenyan preprocess run <slug> --segment <segment-id>
```

## Agent constraints

- **Never** load an entire large `normalized-text.txt` into context.
- **Always** run `validate-artifacts` after a batch of segment work.
- **Stop** on non-zero CLI exit and run `show` (or read `*-review.json`) for the blocked segment.
- **Prefer** `run <slug>` over hand-picking UUIDs when the editor wants to continue incrementally.

## Reference

- Editor journey: [architecture/preprocessing/editor-workflow.md](../../../architecture/preprocessing/editor-workflow.md)
- CLI behavior: [architecture/cli-spec.md](../../../architecture/cli-spec.md)
- Artifact layout: [architecture/preprocessing/intermediate-artifacts.md](../../../architecture/preprocessing/intermediate-artifacts.md)
- Upstream chapter work: [preparing-source-structure](../preparing-source-structure/SKILL.md)
