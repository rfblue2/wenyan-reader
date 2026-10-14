# Preprocessing

## Purpose

Define the local editorial pipeline for turning a full Classical Chinese document into reader-ready content packages.

The reader app consumes curated local files. LLMs may assist preprocessing, but runtime reading should not depend on live LLM calls.

## Design Principles

- Treat every source input as a full document.
- Use LLMs for content-bearing decisions.
- Use deterministic code for validation, packaging, IDs, hashes, and resumability.
- Process large documents in bounded jobs, down to a text segment whenever possible.
- Preserve intermediate artifacts so the pipeline can be audited, retried, and improved.
- Keep final reader files separate from preprocessing artifacts.

## Subdocs

- [Model Strategy](../architecture/model-strategy.md)
- [Operation Scope](../spec/operation-scope.md)
- [Pipeline Stages](../spec/pipeline.md)
- [Job Execution](../architecture/job-execution.md)
- [Editor Workflow](editor-guide.md)
- [Preprocessing CLI Spec](../spec/cli.md)
- [CLI Tech Stack](../architecture/cli.md)
- [Intermediate Artifacts](../spec/artifacts.md)
- [Source Grounding](../spec/source-grounding.md)
- [Review And Quality Jobs](../spec/quality-gates.md)

## Pipeline Overview

```mermaid
flowchart LR
  FullDocument[Full Document Source] --> Normalize[Normalize]
  Normalize --> DiscoverStructure[Discover Structure]
  DiscoverStructure --> ChapterPass[Chapter Passes]
  ChapterPass --> ParagraphJobs[Paragraph Structure Jobs]
  ParagraphJobs --> SegmentJobs[Focused Segment Subjobs]
  SegmentJobs --> DraftParagraph[Draft Paragraph Package]
  DraftParagraph --> Validate[Structural Validation]
  Validate --> ContentQA[Review And Quality Jobs]
  ContentQA --> Package[Reader Document Package]
```

## Final Outputs

The pipeline produces the local storage package consumed by the reader:

- `document.json`
- `glosses/index.json`
- `chapters/*/chapter.json`
- `chapters/*/paragraphs/*.json`

Generated intermediate files are useful, but the reader should depend only on validated package files.
