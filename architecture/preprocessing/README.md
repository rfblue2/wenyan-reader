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

- [Model Strategy](model-strategy.md)
- [Operation Scope](operation-scope.md)
- [Pipeline Stages](pipeline-stages.md)
- [Job Execution](job-execution.md)
- [Editor Workflow](editor-workflow.md)
- [Preprocessing CLI Spec](../cli-spec.md)
- [CLI Tech Stack](../tech-stack/cli.md)
- [Intermediate Artifacts](intermediate-artifacts.md)
- [Source Grounding](source-grounding.md)
- [Review And Quality Jobs](review-and-quality-jobs.md)

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
