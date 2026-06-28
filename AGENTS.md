# AGENTS.md

## Project Context

This repo is designing a local Classical Chinese reader. The app should consume curated local content files; LLMs are used only during preprocessing, never at reader runtime.

Most project details live in the architecture docs. Start there before making design changes, especially the docs covering:

- Final reader content shape.
- Preprocessing overview and pipeline stages.
- Preprocessing CLI commands and status behavior.
- Editor-facing user flows.
- Resumable artifact layout and effective status rules.
- Job graph, resumability, and failure behavior.
- Validation and review passes.

## Vocabulary

- `document`: the canonical source and content unit.
- `chapter`: a top-level structural division within a document.
- `paragraph`: a structural unit used for context framing and segment boundary discovery.
- `segment`: unit of text shown to reader and also smallest unit of text to preprocess
- `artifact`: an intermediate preprocessing file used for auditability, validation, reruns, and packaging.

## Preprocessing Principles

- Preserve intermediate artifacts for auditability and reruns.
- Derive effective status from the artifact graph on disk, not only from manifest metadata.
- Missing artifacts are pending; downstream artifacts with missing or changed inputs are stale.
- Artifact-producing commands should write temporary files first and atomically promote final artifacts only after validation.
- The reader package should depend only on validated final files.

## Editing Guidance

- Follow [Coding Style](architecture/coding-style.md) for Python layer boundaries, Pydantic usage, ports, and static typing.
- Keep architecture docs concise and cross-link rather than duplicating large sections.
- When changing CLI behavior, update the CLI spec and any affected workflow examples.
- When changing artifact shapes or status semantics, update the artifact documentation.
- After doc edits, check terminology against the vocabulary above.
