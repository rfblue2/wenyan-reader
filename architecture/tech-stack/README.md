# Tech Stack

## Purpose

Record framework, tooling, and implementation choices for the Classical Chinese reader project.

Behavioral requirements live in the other architecture docs. This folder records how those requirements are implemented.

## Subdocs

- [CLI](cli.md)
- [Web App](webapp.md)

## Scope For Now

The first implementation stage focuses on the preprocessing CLI. The reader web app is deferred; see [Web App](webapp.md).

Command behavior, artifact paths, status semantics, flags, and output shapes are defined in the [CLI Spec](../cli-spec.md). The CLI tech stack doc covers libraries, project structure, and implementation patterns only.

## Shared Constraints

- The app runs locally for development.
- Production deployment is out of scope for the first stage.
- Runtime reading should not depend on live LLM calls.
- Content should be stored in local files.
- The reader should load large documents incrementally.
- The app should not store local user state in the first stage.

## Cross-Cutting Decisions

These apply to the CLI now and to the web app later:

| Concern | Choice | Notes |
| --- | --- | --- |
| Content IDs | UUID v4 | Matches [Storage Format](../storage-format.md). |
| JSON on disk | UTF-8, pretty-printed in examples | Production writers may compact; readers must accept either. |
| Shared models | Pydantic v2 in `wenyan-models` | Single source of truth for reader package files, preprocessing artifacts, and status payloads. CLI and web app both depend on this library. |
| Schema export | JSON Schema from Pydantic models | Generated schemas support web-app type generation and non-Python validation when needed. |
| Hashing | SHA-256, prefixed `sha256:` | Used for source, normalized text, and artifact input hashes. |

## Shared Library Strategy

Define content shapes once in `wenyan-models` and reuse them across preprocessing and reading:

- Reader package models mirror [Storage Format](../storage-format.md).
- Preprocessing artifact models mirror [Intermediate Artifacts](../preprocessing/intermediate-artifacts.md).
- Status payload models mirror the examples in [CLI Spec](../cli-spec.md).

The shared library should stay free of CLI, LLM, and UI dependencies so it remains safe to import from any runtime. Preprocessing and reading code validate against the same models rather than maintaining parallel JSON definitions.

## Open Questions

- Where should generated JSON Schema files live in the repo, and how should the web app consume them?
- Should SQLite be introduced early for indexing, or deferred until search/import requirements are clearer?
