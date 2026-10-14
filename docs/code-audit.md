# Code Audit — Remaining Items

The original audit (static checking, typed boundaries, segment job runner, layering ports, mechanical cleanups) is **done** — see commits `dd96f57` through `f661c4a`. CI runs ruff, mypy, and pytest on every push/PR.

This doc tracks **open code-quality work** only. Pipeline correctness and cost items live in [architecture-audit.md](architecture-audit.md).

## High

### Gloss decision ↔ entry linking

When the LLM emits `create-new` with placeholder `glossId: "new"` while `newGlosses` uses separate ids (`new-001`, …), status and assembly cannot resolve pinyin/gloss. The prompt asks for UUID v4 on new entries but does not state the invariant that **`glossDecisions[].glossId` must equal the matching `newGlosses[].id`**.

- Add a post-LLM normalizer (pair by token order or surface) or reject at promote time.
- Tighten `segment-gloss.md` with the explicit cross-reference rule.
- Gloss review should fail when decisions do not resolve to entries.

Preferred long-term fix: prevent the mismatch at the call site instead of normalizing after — see [llm-correctness.md](llm-correctness.md).

## Medium

### Shared review artifact model

`TokenizationReviewArtifact`, `GlossReviewArtifact`, and `GrammarReviewArtifact` are field-for-field identical; `ContextReviewArtifact` adds `sourceGrounding`. Extract a shared base (keep per-kind types for dispatch if useful).

### Status derivation uses untyped dict construction

`core/status/derivation.py` builds payloads via `Model.model_validate({...})` with hand-built camelCase dicts. Construct with typed kwargs (or alias kwargs) so the status layer is statically checked.

### Deterministic hooks in segment runner

`segment_runner` is the right place to add **prompt-version hashing** in `input_hash` and **deterministic post-validation** at promote time (tokenization offsets/coverage, gloss decision resolution). See architecture audit §2.1–2.2.

## Low

### CLI constructs adapters outside bootstrap

`preprocess.py` instantiates `FilesystemStatusReader` and `FilesystemGraphValidator` directly. Wire both through `JobContext` (ports already exist).

### `artifact_ref.py` factory boilerplate

~180 lines of near-identical wrappers around `_make_ref`. Acceptable for call-site safety; optional codegen or `functools.partial`-style generation.

## Tests

| Gap | Notes |
|-----|--------|
| `split-segments` reconstruction failure | No test — check not implemented yet ([architecture-audit §2.1](architecture-audit.md)) |
| Stale approved review | Hand-edited draft + unchanged review should not show complete ([architecture-audit §2.3](architecture-audit.md)) |

`prune` CLI regression test added in `tests/cli/test_prune_cli.py`.

## Suggested order

1. Gloss id linking (normalizer + prompt + review gate)
2. Deterministic promote-time validation in `segment_runner`
3. Shared review artifact base
4. Status derivation typed construction
5. CLI adapters on `JobContext`
