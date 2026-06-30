# Editor Workflow

## Purpose

Describe how a developer/editor adds a new Classical Chinese document to the collection and interacts with the preprocessing pipeline.

The editor should be able to run the pipeline incrementally, inspect intermediate artifacts, repair or rerun small units, and eventually package a validated reader document. The default interface should be a CLI because preprocessing is local, file-oriented, resumable, and likely to be run from a developer checkout.

## Persona

The editor is a developer or editorial maintainer who:

- Adds source documents to the repository.
- Chooses when to run each preprocessing stage.
- Reviews generated structure and content before final packaging.
- Reruns failed or revised units without restarting the whole document.
- May eventually wire the same commands into CI or another automation system.

The editor should not manually orchestrate low-level retry bookkeeping, rate-limit handling, prompt construction, hash checking, or artifact path management. Those are pipeline responsibilities.

## Source Ingestion

The editor adds raw documents under a slug-owned source directory and registers them in a document-level index:

```text
sources/
  registry.yaml
  documents/
    sunzi-bingfa/
      source.txt
      document.yaml
```

`registry.yaml` lists documents only. It does not contain chapter, paragraph, or segment structure — that structure is produced by preprocessing and stored under `preprocess/documents/<document-id>/`.

CLI commands accept `<document-id>` as a UUID or as a source slug resolved through the registry. `ingest-document` accepts a source directory only.

Each slug directory contains:

- `source.txt` — the full document text.
- `document.yaml` — ingest-time metadata.

The source metadata should include enough information to create the stable document manifest:

- Title.
- Source language and script assumptions.
- Source provenance.
- Punctuation and normalization policy.
- Optional source headings or known chapter markers.
- Optional editor notes to pass as grounding material.

The raw source is always treated as a full document. A chapter excerpt or paragraph excerpt can be useful for testing, but it should not become the canonical source unit.

## CLI Reference

The editor workflow uses the preprocessing CLI, but this document describes the editor journey rather than command internals. See [CLI Spec](../cli-spec.md) for command behavior, options, outputs, and status payloads.

## User Flow: Add A New Document Step By Step



### 1. Ingest And Normalize

The editor adds the raw document and runs:

```shell
wenyan preprocess ingest-document sources/documents/sunzi-bingfa
```

The editor then checks the normalized text and source metadata before asking the pipeline to infer structure.

- Confirm the normalized text still represents the intended source.
- Adjust source metadata or normalization policy if needed.



### 2. Define Chapter Structure (interactive)

Chapter boundaries are prepared interactively with a local agent using the [preparing-source-structure](../../.cursor/skills/preparing-source-structure/SKILL.md) skill. The agent and editor write `preprocess/documents/<document-id>/structure/chapter-proposal.json` after agreeing on boundaries.

```shell
wenyan preprocess status <document-id>
wenyan preprocess validate-artifacts <document-id>
```

The editor reviews the chapter list before processing individual chapters.

- Inspect chapter boundaries and titles in `chapter-proposal.json`.
- Revise the proposal with the agent before moving deeper.



### 3. Generate Paragraph Structure For A Chapter

The editor runs:

```shell
wenyan preprocess split-paragraphs <document-id> --chapter <chapter-id>
wenyan preprocess status <document-id> --chapter <chapter-id>
```

The editor reviews paragraph boundaries for the selected chapter.

- Review paragraph boundaries.
- Rerun or repair the chapter's paragraph proposal if boundaries are poor.



### 4. Generate Segment Structure For A Paragraph

The editor runs:

```shell
wenyan preprocess split-segments <document-id> --paragraph <paragraph-id>
wenyan preprocess review-paragraph-structure <document-id> --paragraph <paragraph-id>
wenyan preprocess status <document-id> --paragraph <paragraph-id>
```

The editor reviews segment boundaries and paragraph-level context before running focused segment subjobs.

- Review segment boundaries when needed.
- Decide whether paragraph-level context notes belong at paragraph scope or should move to segment scope.



### 5. Run Focused Segment Subjobs

The editor can process one segment through focused, resumable commands:

```shell
wenyan preprocess tokenize-segment <document-id> --segment <segment-id>
wenyan preprocess review-segment-tokenization <document-id> --segment <segment-id>
wenyan preprocess gloss-segment <document-id> --segment <segment-id>
wenyan preprocess review-segment-gloss <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-grammar <document-id> --segment <segment-id>
wenyan preprocess review-segment-grammar <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-context <document-id> --segment <segment-id>
wenyan preprocess review-segment-context <document-id> --segment <segment-id>
wenyan preprocess status <document-id> --segment <segment-id>
```

Or run the same stage across all pending segments under a paragraph:

```shell
wenyan preprocess tokenize-segment <document-id> --paragraph <paragraph-id>
wenyan preprocess gloss-segment <document-id> --paragraph <paragraph-id>
wenyan preprocess annotate-segment-grammar <document-id> --paragraph <paragraph-id>
wenyan preprocess annotate-segment-context <document-id> --paragraph <paragraph-id>
```

The editor only needs to intervene when focused segment components fail review or become blocked.

- Inspect failed or blocked segment subjobs.
- Manually repair content only when automated repair is exhausted or editorial judgment is required.



### 6. Assemble The Paragraph

Once all segment subjobs for a paragraph are complete (all eight subjobs with approved reviews for every segment), the editor runs paragraph assembly explicitly. `run preprocess` does not auto-advance to assembly.

```shell
wenyan preprocess assemble-paragraph <document-id> --paragraph <paragraph-id>
wenyan preprocess review-paragraph-assembly <document-id> --paragraph <paragraph-id>
wenyan preprocess status <document-id> --paragraph <paragraph-id>
```

The editor reviews the staged `jobs/assembly/paragraph-id/package.json` and assembly review before packaging. A paragraph is not complete until both assembly commands succeed. See [Storage Format](../storage-format.md) for the reader paragraph schema.



### 7. Package The Document

After enough paragraphs are complete, the editor can package the document:

```shell
wenyan preprocess package-document <document-id>
```

**Stubbed.** When implemented, `package-document` promotes approved `jobs/assembly/paragraph-id/package.json` files to `content/documents/document-id/chapters/chapter-id/paragraphs/paragraph-id.json` and builds the rest of the reader package.

The editor reviews the packaged reader files through normal code review before adding them to the collection.

## User Flow: Chain A Larger Run

Once the editor trusts the earlier boundaries, they can chain segment work:

```shell
wenyan preprocess run <document-id>
wenyan preprocess run <document-id> --next-paragraph
```

`run` with no flags processes the next incomplete segment through all subjobs. `--next-paragraph` prepares segment structure for the next paragraph that lacks a draft.

The editor still uses status output to decide where to inspect next:

```shell
wenyan preprocess status <document-id>
wenyan preprocess status <document-id> --chapter <chapter-id>
wenyan preprocess status <document-id> --paragraph <paragraph-id>
wenyan preprocess validate-artifacts <document-id>
```

This keeps CI or batch execution possible without making the editor give up incremental control.

## User Flow: Inspect And Repair A Blocked Segment

When status shows a blocked segment, the editor drills into the segment and review report:

```shell
wenyan preprocess status <document-id> --segment <segment-id>
wenyan preprocess review-report <document-id> --segment <segment-id>
```

The editor then fixes the underlying issue or reruns the focused component after adjusting inputs. The specific command behavior and status payload shape live in the CLI spec.

## User Flow: Reject Generated Output

If the editor is unhappy with generated output, the simplest manual control should be deleting the artifact they do not accept. The pipeline status should be derived from the artifact graph on disk, so deletion should automatically show up in the next status call.

Example: the editor dislikes the generated grammar notes for one segment.

```shell
rm preprocess/documents/<document-id>/jobs/segments/<segment-id>/grammar-notes.json
wenyan preprocess status <document-id> --segment <segment-id>
wenyan preprocess annotate-segment-grammar <document-id> --segment <segment-id>
wenyan preprocess review-segment-grammar <document-id> --segment <segment-id>
```

Expected result:

- `annotate-segment-grammar` becomes pending because its output is missing.
- `review-segment-grammar` becomes stale or blocked by upstream because its reviewed input no longer exists.
- Other independent components, such as gloss and context notes, remain complete if their inputs are unchanged.
- Paragraph assembly becomes stale if it had already consumed the deleted grammar-note artifact.

This keeps editorial rejection local and transparent. A future CLI helper could wrap deletion in an explicit command, but plain artifact deletion should be enough for the status model to reflect editor intent.

## User Flow: Validate Artifact Integrity

The editor can periodically validate that the artifact graph is internally consistent, especially after an interrupted run, a failed LLM call, manual deletion, or manual artifact edit.

```shell
wenyan preprocess validate-artifacts <document-id>
wenyan preprocess validate-artifacts <document-id> --chapter <chapter-id>
wenyan preprocess validate-artifacts <document-id> --paragraph <paragraph-id>
wenyan preprocess validate-artifacts <document-id> --segment <segment-id>
```

This command should not generate new content. It should report missing outputs, stale downstream artifacts, dangling references, invalid JSON, schema errors, and leftover temporary files that should not count as completed artifacts.

## Orchestration Boundary

The editor orchestrates editorial checkpoints:

- When to move from document ingestion to chapter discovery.
- Which chapter to process next.
- Which paragraph or segment needs rerun or manual repair.
- Whether generated content is good enough to package.

The pipeline orchestrates execution mechanics:

- Artifact paths.
- Input hashes.
- Prompt versions.
- Model routing.
- Retries for transient provider failures and blocking on review rejection.
- Rate limits and concurrency.
- Validation and review job ordering.
- Incremental caching and resumability.

## Open Questions

- Should edited intermediate artifacts be first-class inputs, or should manual fixes happen through patch files or explicit override commands?
- What is the acceptance UX for chapter, paragraph, and segment boundaries: edit JSON directly, run an interactive command, or rely on normal code review?

