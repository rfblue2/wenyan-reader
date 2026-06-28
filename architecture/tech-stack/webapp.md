# Web App Tech Stack

## Purpose

Reserve a dedicated document for reader app framework, tooling, and implementation choices.

This has not been designed yet. The first implementation stage focuses on the preprocessing CLI. See [CLI](cli.md).

## Decisions To Make

Frontend decisions:

- App framework.
- Routing approach.
- Styling approach.
- State management.
- URL representation for the current document, chapter, paragraph, and segment.
- Rendering strategy for clickable Classical Chinese tokens.

Content loading decisions:

- How the app discovers local reader packages on disk.
- Build-time or runtime validation strategy for loaded content.
- Incremental loading strategy for large documents.

Development decisions:

- Package manager.
- Test runner.
- Formatter and linter.
- Local dev server.

## Current Constraints

These come from [App UX](../app-ux.md) and [Storage Format](../storage-format.md):

- The reader consumes validated local package files only.
- Runtime reading must not depend on live LLM calls.
- Large documents should load incrementally.
- The first stage does not store local user state.
- Content shapes should come from the shared `wenyan-models` library; see [Tech Stack README](README.md).

## Open Questions For Later

- Should the app be built with a simple SPA stack or a framework with filesystem routing?
- How should the web app consume shared models: generated TypeScript types from exported JSON Schema, a Python sidecar, or both?
- Should validation run as part of app startup, tests, or a dedicated content build step?
- Should SQLite be introduced early for indexing, or deferred until search/import requirements are clearer?

## Related Docs

- [App UX](../app-ux.md)
- [Storage Format](../storage-format.md)
- [CLI](cli.md)
