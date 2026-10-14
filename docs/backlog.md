# Project backlog

Editor-captured ideas for what to work on next. When asked what is left to do, suggest from this list (and cross-check against current repo state — some items may be partially done).

## Backlog

1. **Architecture and coding-style hygiene** — Improve docs around consistency, completeness of features, and keeping architecture docs in sync with the code (reduce drift).

2. **DRY and simplify** — Make the codebase DRYer: reduce duplication and complexity in both implementation and the preprocessing workflow.

3. **Reader web app** — Build the full reader web application (consumes packaged local content; no LLM at runtime).

4. **Document / PDF exporter** — Export curated documents (e.g. PDF or similar) from packaged content.

5. **Preprocessor CI** — Continuous integration for the preprocessing pipeline (validation, tests, and/or artifact checks in CI).

6. **Automated context note annotation** — Automate context-note drafting with a higher-quality model (today context notes are skill/CLI-driven with stubbed annotate/review commands).

## Open findings

Carried over from the removed architecture and code audits. To be re-audited.

### Correctness

- **Segment reconstruction check** — `split-segments` writes a PASSED validation without checking that segments concatenate back to the paragraph text. `PureSpanValidator.validate_segments` exists but is unused.
- **Tokenization validation** — no deterministic check of `surface == text[start:end]`, ordering, non-overlap, or coverage of non-punctuation characters at promote time.
- **Stale segment reviews** — status counts an approved review as complete without comparing `review.input_hash` to the current draft. Re-running a rejected review with unchanged input skips with exit 0.
- **`validate-artifacts` scope** — checks only the normalized document; chapter/paragraph/segment scopes reuse the document check.
- **Prompt version in input hash** — editing a prompt invalidates nothing. Include a prompt template hash in each job's `input_hash`.
- **Gloss id linking** — `glossDecisions[].glossId` can fail to match `newGlosses[].id`. See [LLM output correctness](proposals/llm-output-correctness.md).
- **Gloss review side effect** — `review-segment-gloss` merges into `indexes/glossary-draft.json`; nothing removes orphans. Move the merge to assembly or rebuild at package time.
- **Paragraph context notes untyped** — `ParagraphDraft.paragraph_context_notes` are raw dicts; assembly silently drops notes with bad anchors.
- **`attempts` always 1** — increment from the prior artifact or remove the field.

### Cost and model routing

- **Per-role model routing** — one provider/model for all jobs, so review is self-review by the drafting model. Add draft/review/structure roles with dev/prod profiles.
- **Merge segment reviews** — collapse tokenization, gloss, and grammar review into one segment review call with per-component verdicts.
- **Structured output enforcement** — see [LLM output correctness](proposals/llm-output-correctness.md) phases 1–4.

### CLI and workflow

- **Stub commands** — decide whether to cut or implement `review-paragraph-structure` and `review-report`.
- **`run` halts at context** — consider stopping cleanly before the context stage instead of a `not-implemented` failure.
- **Unimplemented flags** — `--concurrency` and `--continue-on-blocked`.

### Code quality

- Shared base for tokenization/gloss/grammar review artifact models.
- Typed construction in `core/status/derivation.py` instead of `model_validate({...})` dicts.
- Wire `FilesystemStatusReader` and `FilesystemGraphValidator` through `JobContext` instead of constructing in `cli/preprocess.py`.
- Tests: `split-segments` reconstruction failure; stale approved review.
