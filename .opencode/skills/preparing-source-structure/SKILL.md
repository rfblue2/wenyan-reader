---
name: preparing-source-structure
description: >-
  Guides interactive source normalization and chapter boundary work between an
  editor and a local agent. Use when preparing a new Classical Chinese document,
  normalizing source text, defining chapter structure, registering a source slug,
  or before running downstream preprocessing (split-paragraphs and later).
---

# Preparing Source Structure

Chapter boundaries are an **editorial decision** made interactively with the user. There is no `split-chapters` CLI command.

Mechanical normalization uses the existing ingest CLI. Chapter structure is negotiated, written by hand, and validated before later pipeline stages.

## When to use this skill

- Adding a new document under `sources/documents/<slug>/`
- Normalizing raw source text for preprocessing
- Defining or revising chapter boundaries
- Replacing or repairing `structure/chapter-proposal.json`

## Roles

| Role | Responsibility |
| --- | --- |
| **Editor (user)** | Final authority on normalization policy exceptions, chapter titles, and boundary placement |
| **Agent** | Apply normalization rules, surface heading evidence, propose boundaries, write artifacts, run validation |

## Workflow

Copy and track progress:

```text
- [ ] 1. Source directory and registry entry exist
- [ ] 2. document.yaml metadata is complete
- [ ] 3. Normalized artifacts produced (ingest)
- [ ] 4. Editor reviewed normalized text sample
- [ ] 5. Chapter boundaries drafted collaboratively
- [ ] 6. chapter-proposal.json written
- [ ] 7. Span validation passes
- [ ] 8. Hand off to split-paragraphs
```

### Step 1–2: Source layout

```text
sources/
  registry.yaml
  documents/
    <slug>/
      source.txt
      document.yaml
```

Register the slug in `sources/registry.yaml`. See [normalization-rules.md](normalization-rules.md) for `document.yaml` fields.

### Step 3: Normalize (mechanical)

Run ingest — do not hand-author `normalized-document.json` or byte indexes:

```shell
wenyan preprocess ingest-document sources/documents/<slug>
```

This writes:

```text
preprocess/documents/<document-id>/
  normalized-document.json
  normalized-text.txt
```

Record the assigned `documentId` in the registry if ingest added one.

### Step 4: Review normalization with the editor

- Read **samples** from `normalized-text.txt` (start, middle, end, and any flagged regions). For large documents, use slice reads — never load the full file into context at once.
- Compare against `source.txt` only where the editor asks or where normalization policy is unclear.
- Confirm `document.yaml` `normalization` settings match editor intent.
- If policy must change, update `document.yaml` and rerun ingest with `--force`.

### Step 5: Interactive chapter splitting

Work **with** the editor section by section:

1. Scan for heading evidence (卷, 篇, 第N, source-specific markers) using slices — cite offsets and quoted lines.
2. Propose chapter boundaries; explain literary or pedagogical rationale.
3. Ask before merging/splitting non-obvious regions (preamble, preface, appendices, commentary blocks).
4. Iterate until the editor explicitly approves the boundary list.

**Do not** finalize boundaries from headings alone. Headings are evidence, not ground truth.

For large documents, work chapter-by-chapter: agree on the next boundary pair before moving on.

### Step 6: Write chapter proposal

Write `preprocess/documents/<document-id>/structure/chapter-proposal.json` per [chapter-structure-format.md](chapter-structure-format.md).

Use:

- `promptVersion`: `editor-chapter-structure-v1`
- `model`: `editor`
- `inputHash`: hash of the normalized manifest hash (see format doc)
- Fresh UUID v4 for each new chapter `id`; reuse IDs when only titles/rationale change

### Step 7: Validate

Check span rules in [chapter-structure-format.md](chapter-structure-format.md), then:

```shell
wenyan preprocess validate-artifacts <document-id>
```

Write `structure/chapter-proposal.validation.json` with `"status": "passed"` and empty `checks` when validation succeeds.

If validation fails, fix the proposal with the editor — do not proceed to paragraph splitting.

### Step 8: Hand off

Once chapter structure is accepted:

```shell
wenyan preprocess split-paragraphs <document-id> --chapter <chapter-id>
```

Downstream preprocessing (paragraphs, segments, tokenization) stays on the CLI.

## Agent constraints

- **Never** load an entire large `normalized-text.txt` or `source.txt` into context; read slices by character offset.
- **Never** propose automated chapter-discovery CLI commands — chapter structure is interactive only.
- **Always** get explicit editor approval before writing `chapter-proposal.json`.
- **Preserve** stable chapter UUIDs when revising boundaries unless the editor requests a reset.
- **Do not** change Classical Chinese characters during normalization unless the editor requests it and `document.yaml` records the policy.

## Reference

- Normalization rules and policies: [normalization-rules.md](normalization-rules.md)
- Chapter proposal JSON shape and span invariants: [chapter-structure-format.md](chapter-structure-format.md)
- Artifact layout: [architecture/preprocessing/intermediate-artifacts.md](../../../architecture/preprocessing/intermediate-artifacts.md)
- Editor journey (downstream CLI): [architecture/preprocessing/editor-workflow.md](../../../architecture/preprocessing/editor-workflow.md)
