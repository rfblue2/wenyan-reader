# Proposal: Artifact Graph Integrity

**Status:** proposed. Current rules: [Artifacts — Effective status](../spec/artifacts.md#effective-status), [CLI — validate-artifacts](../spec/cli.md#validate-artifacts). Backlog: G-C3, G-C4, G-C5, G-V1, G-W9.

Make status trustworthy: every artifact knows its inputs, stale outputs never count as complete, and `validate-artifacts` catches anything that would make progress misleading.

## Staleness

An artifact is **stale** when one of its declared inputs is missing, has a different hash, or was produced with an incompatible prompt version. Stale artifacts never count as complete.

When an editor deletes or changes an artifact:

- The deleted component becomes `pending`.
- Every downstream artifact that consumed it becomes `stale` or `blocked-by-upstream`, even though its file still exists.
- A rerun regenerates only the missing or stale component and what consumes it.

Applies to every component: segment drafts and reviews (today only assembly checks hashes), paragraph and chapter proposals against their source text, and the reader package against assembly.

## Status output

- Rollups count complete, in-progress, pending, failed, and blocked units at every scope.
- Each failed or blocked unit shows its last validation or review error, including at paragraph and chapter level.

## Writes

1. Write generated content to temporary paths.
2. Parse and validate the temporary artifacts.
3. Promote with atomic rename only when every output of the component is present and consistent.

Coupled outputs promote as a unit: `split-segments` must never leave segment `input.json` files pointing at a missing draft. If the set cannot be promoted consistently, the component stays pending or failed. Leftover temp files are ignored by status and reported by validation.

## `validate-artifacts`

Stricter than `status`: it reports structural problems, generates nothing, and exits non-zero on any invalid, dangling, stale, or partially written artifact. At document, chapter, paragraph, or segment scope it checks:

- Every expected artifact is present or explicitly pending.
- Every present artifact parses against its schema.
- Every declared input hash matches the current upstream artifact.
- No reference to a missing chapter, paragraph, segment, note, token, gloss, or source.
- No downstream artifact is complete while an upstream dependency is missing or stale.
- No reader package file references missing package files or preprocessing artifacts.
- No temporary file is treated as a real artifact.

Implementation home: a graph walker behind the existing `GraphValidator` port, reusing the assembly and package validators.
