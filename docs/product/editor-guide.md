# Editor Guide

> **Guide** — how an editor takes a document from raw text to a reader package. Command details: [CLI](../spec/cli.md). Files: [Artifacts](../spec/artifacts.md).

The editor is a developer or editorial maintainer working in a local checkout. They choose when to run each stage, review output at each checkpoint, and rerun small units. The pipeline handles paths, hashes, skip-on-rerun, and status.

All commands run from the repo root as `uv run wenyan preprocess …`. Units can be addressed by UUID or by ordinal (`--chapter 1 --paragraph 2 --segment 3`).

## 1. Add a source

```text
sources/
  registry.yaml              document list (ids filled in by ingest)
  documents/<slug>/
    source.txt               full document text
    document.yaml            title, language, provenance, normalization policy, headings
```

A source is always a full document, never an excerpt.

## 2. Ingest

```shell
uv run wenyan preprocess ingest-document sources/documents/sunzi-bingfa
```

Check `preprocess/documents/<id>/normalized-text.txt` still matches the intended source.

## 3. Define chapters (interactive)

Work with an agent using the [preparing-source-structure](../../.opencode/skills/preparing-source-structure/SKILL.md) skill to agree on chapter boundaries. The agent writes `structure/chapter-proposal.json`.

```shell
uv run wenyan preprocess status sunzi-bingfa
```

## 4. Split a chapter into paragraphs

```shell
uv run wenyan preprocess split-paragraphs sunzi-bingfa --chapter 1
uv run wenyan preprocess status sunzi-bingfa --chapter 1
```

Review the boundaries. To redo, rerun with `--force`.

## 5. Split a paragraph into segments

```shell
uv run wenyan preprocess split-segments sunzi-bingfa --chapter 1 --paragraph 1
uv run wenyan preprocess status sunzi-bingfa --chapter 1 --paragraph 1
```

Review segment boundaries and any paragraph-level context notes in `jobs/paragraphs/<id>/draft.json`.

## 6. Process segments

Either chain all LLM components for the next incomplete segment:

```shell
uv run wenyan preprocess run sunzi-bingfa
```

Or run components one at a time (`--paragraph` alone runs the draft jobs for every segment in the paragraph):

```shell
S="--chapter 1 --paragraph 1 --segment 1"
uv run wenyan preprocess tokenize-segment sunzi-bingfa $S
uv run wenyan preprocess review-segment-tokenization sunzi-bingfa $S
uv run wenyan preprocess gloss-segment sunzi-bingfa $S
uv run wenyan preprocess review-segment-gloss sunzi-bingfa $S
uv run wenyan preprocess annotate-segment-grammar sunzi-bingfa $S
uv run wenyan preprocess review-segment-grammar sunzi-bingfa $S
```

Then draft and review context notes with an agent: "Draft context notes for sunzi-bingfa ch1 p1 seg1" ([drafting-context-notes](../../.opencode/skills/drafting-context-notes/SKILL.md), then [reviewing-context-notes](../../.opencode/skills/reviewing-context-notes/SKILL.md)). `run` stops at context until these exist.

Inspect a segment at any time:

```shell
uv run wenyan preprocess status sunzi-bingfa $S
```

## 7. Assemble the paragraph

When every segment in the paragraph has all eight components complete:

```shell
uv run wenyan preprocess assemble-paragraph sunzi-bingfa --chapter 1 --paragraph 1
```

Review `jobs/assembly/<paragraph-id>/package.json`.

## 8. Package the document

```shell
uv run wenyan preprocess package-document sunzi-bingfa
```

Writes every assembled paragraph to `content/documents/<id>/`. Review and commit the result with the matching `preprocess/` tree.

## Fixing output

| Situation | Action |
|---|---|
| Review rejected (segment `blocked`) | Read findings in `status --segment`. Rerun the draft job with `--force` (deletes the old review), then the review. |
| Unhappy with any artifact | Delete it. Status shows that component `pending`; rerun it. |
| Boundaries changed after rerunning `split-paragraphs` / `split-segments` | `uv run wenyan preprocess prune sunzi-bingfa` removes orphaned segment and stale assembly dirs. |
| Assembly stale after segment edits | Rerun `assemble-paragraph`. |

Deleting a draft does not mark its review stale: the review shows `pending` until the draft is regenerated. Downstream drafts (e.g. glosses after re-tokenizing) are not invalidated automatically; delete them too.

## Open questions

- Should hand-edited artifacts be first-class inputs, or should fixes go through patch files or override commands?
- How should boundaries be accepted: edit JSON, an interactive command, or code review?
