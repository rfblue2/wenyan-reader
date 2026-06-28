# Preprocess `show` Command Design

## Problem

Segment preprocessing artifacts (`glosses.json`, `gloss-review.json`, etc.) are machine-oriented JSON files buried under UUID paths. Editors reviewing gloss quality need a human-readable view without manually resolving IDs or pretty-printing JSON.

## Goal

Implement `wenyan preprocess show` so an editor can inspect one segment's source text and generated outputs in the terminal.

## Command

```shell
wenyan preprocess show <document-id> --segment <segment-id> [--chapter <ref>] [--paragraph <ref>] [--json]
```

- `--segment` is required (UUID or ordinal; ordinals require `--paragraph`, which may require `--chapter`).
- Scope resolution reuses `resolve_status_scope` from the status command.
- `--json` emits a structured `SegmentShowView` payload for agents and tooling.

## Output (human)

1. **Location header** — document slug, chapter/paragraph/segment handles (e.g. `#1 · #2 · #3`) plus dim UUIDs.
2. **Segment text** — full source string, prominent.
3. **Glosses table** — when `glosses.json` exists, one row per tokenized token:
   - Token (surface)
   - Pinyin
   - Gloss
   - Decision (`reuse-existing` / `create-new`)
   - Rows resolve gloss IDs from `newGlosses` or `candidateGlosses` on segment input.
4. **Tokenization** — when glosses are absent but tokenization exists, list token surfaces only.
5. **Review findings** — for each review artifact present, show status (`approved` / `rejected`) and bullet findings with messages.
6. **Component summary** — compact list of all eight segment subjob statuses (same rollup as `status --segment`).

Pending components are omitted from content sections but appear in the component summary.

## Output (JSON)

`SegmentShowView` model with:

- Location IDs and handles
- `text`
- `tokens`: joined token + gloss rows
- `reviews`: review kind, status, findings
- `components`: same shape as segment status components

## Non-goals (this slice)

- `review-report` command (may share rendering helpers later).
- Grammar/context note bodies (not implemented yet).
- Interactive editing or artifact mutation.

## Layering

```text
cli/preprocess.py       command wiring, exit codes
cli/show_output.py      Rich rendering
core/show/segment_view.py   assemble SegmentShowView from artifacts
wenyan_models/show/     Pydantic view models
```

## Related

- [CLI spec](../../architecture/cli-spec.md) — `show` section
- [Editor workflow](../../architecture/preprocessing/editor-workflow.md) — blocked-segment drill-down
