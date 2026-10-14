# Architecture Audit

Audit of the domain architecture, editor workflow, and preprocessing pipeline against the stated goals: simplicity first, correctness via well-placed AI usage, and minimized LLM cost. Findings are ordered by priority within each section.

## Summary

The overall shape is sound: full-document ingestion, LLM-proposed structure with deterministic validation, segment-scoped resumable subjobs, artifact-graph-derived status, and a validated reader package. The main problems are (1) the pipeline spends LLM review calls on checks that should be deterministic, (2) several deterministic checks the architecture promises are not actually implemented, and (3) the model strategy has no per-job routing, so draft/review and dev/prod cost separation exists only as documentation.

## 1. Pipeline simplicity and redundancy

### 1.1 Eight subjobs per segment is too many (HIGH)

Every segment costs 8 LLM-gated steps: 4 drafts + 4 reviews. The four review passes overlap with each other and with checks that can be done in code:

- **Tokenization review** mostly re-checks mechanical properties (offsets, overlaps, punctuation-only tokens, missing coverage) that are deterministically checkable. Only "boundary quality" (name/compound grouping) needs judgment — and gloss review already sees every token with its surface and sense, so it implicitly re-validates boundaries.
- **Grammar review** includes "notes do not conflict with gloss senses", which gloss review also owns.

Recommendation: collapse the three CLI review passes (tokenization, gloss, grammar) into **one segment review call** that runs after drafts exist and returns a per-component verdict (`tokenization: approved/rejected`, `gloss: …`, `grammar: …`). Draft resumability is unchanged — only the rejected draft is re-run. This cuts per-segment LLM calls from 8 to ~5 and removes the overlapping-goals problem the review passes currently have. Keep context review separate since it is skill-driven and source-grounded.

If per-component review artifacts are kept, at minimum gate them behind deterministic pre-validation (see 2.2) so a review call is never spent on mechanically invalid output.

### 1.2 `review-paragraph-structure` should be cut, not implemented (MEDIUM)

It appears in the CLI spec, the editor workflow, and `review-and-quality-jobs.md`, but the command is a stub (`exit 2`). Its checklist (boundaries preserve text, anchors valid) is either deterministic (reconstruction) or already covered by the interactive `preparing-source-structure` workflow plus the editor's explicit review step 4. Recommend removing it from the docs and CLI rather than implementing a fifth LLM review. Same for `review-report`, which is stubbed while `status --segment` already prints review findings.

### 1.3 Context notes: two parallel workflows (LOW)

Context drafting/review is skill-driven while the CLI commands are stubs that point at the skills. This is a reasonable interim (web-grounded research needs an agent), but it means the "eight subjobs" contract is half CLI, half agent, and `run` always halts at context. Fine for now; when backlog item 6 lands, delete the stubs and skills in the same change to avoid a third hybrid state.

## 2. Correctness

### 2.1 `split-segments` never validates reconstruction (HIGH)

```73:73:src/wenyan/jobs/split_segments.py
    validation = ParagraphValidationArtifact(status=ValidationStatus.PASSED, checks=())
```

The validation artifact is written as PASSED unconditionally. The LLM can drop or rewrite paragraph text and the pipeline will happily carry it to the reader package. `PureSpanValidator.validate_segments` exists but is never called. This is the single most important promise in the architecture ("segment strings concatenate back to the paragraph text") and it is unimplemented. Fix: concatenate `draft.segments[*].text` and compare against the paragraph slice before promoting; fail the job otherwise.

### 2.2 No deterministic tokenization validation (HIGH)

`tokenize-segment` promotes LLM output after only dropping punctuation tokens. Nothing verifies `surface == text[start:end]`, ordering, non-overlap, or that every non-punctuation character is covered by some token ("glosses actually cover everything"). Assembly later checks only that each *emitted* token has a gloss decision — a segment whose tokenizer skipped a character passes every deterministic gate. The architecture explicitly assigns offset and coverage checks to deterministic code; today they are delegated to the tokenization-review LLM. Fix: validate offsets/ordering/coverage in code at promote time; reserve the LLM review for boundary-quality judgment only (or fold it into gloss review per 1.1).

### 2.3 Status does not detect stale segment reviews (MEDIUM-HIGH)

`component_unit_status` treats an approved review as COMPLETE without comparing `review.input_hash` to the current draft's hash. The delete-on-rewrite hook (`invalidate_segment_review`) covers CLI reruns, but the documented workflow explicitly encourages hand-editing and hand-writing artifacts (context skills, "delete the artifact you dislike"). A hand-edited `tokenization.json` leaves an approved-but-stale review counted as complete. Assembly status already does hash-based staleness; apply the same rule to the four review components.

Related wrinkle: re-running a review whose artifact is REJECTED but whose input hash is unchanged returns `Skipped("review is current")` with exit 0 — a rejected state reads as success. Skips should only apply to approved reviews.

### 2.4 `validate-artifacts` is a stub relative to its spec (HIGH, drift)

The CLI spec promises schema checks, hash staleness, dangling references, and temp-file detection at four scopes. `FilesystemGraphValidator` checks only that the normalized document and text sidecar exist and hash-match; chapter/paragraph/segment scopes all just call the document check. Meanwhile the skills instruct agents to "**Always** run `validate-artifacts` after a batch of segment work" — the green light it gives is mostly false confidence. Either implement the graph walk (most checks already exist in assembly/package validators and can be reused) or shrink the spec and skill claims to what it does.

### 2.5 `promptVersion` is specified everywhere and implemented nowhere (MEDIUM)

Artifacts, staleness rules, and job metadata all reference prompt versions in the docs; no artifact model or hash includes one. Editing a prompt today invalidates nothing. Cheap fix: include a hash of the prompt template body in each job's `input_hash`.

### 2.6 Reviewer is the drafter (MEDIUM)

One configured model performs both drafting and review, so review approval is self-review and errors correlate (a model that picks the wrong 將 reading is likely to approve it too). The model-strategy doc already implies draft/review separation; the config cannot express it (see 3.1). Route reviews to a different model (or at minimum a different provider/temperature) for genuinely independent checking.

### 2.7 Gloss review has a write side effect (MEDIUM)

`run_review_segment_gloss` merges approved glosses into `indexes/glossary-draft.json`. A review job mutating a document-level index blurs the draft/review boundary, and nothing un-merges if the segment's glosses are later deleted or rejected — the glossary accumulates orphans that `package-document` will happily publish. Move the merge into `assemble-paragraph` (deterministic, and its staleness is already hash-tracked) or rebuild the glossary from approved segment artifacts at package time.

### 2.8 Paragraph-level context notes are unvalidated (MEDIUM)

`ParagraphDraft.paragraph_context_notes` is a tuple of raw dicts. `_fold_paragraph_context_notes` best-effort-parses them and **silently drops** notes with missing/unknown anchors during assembly. The spec requires anchor validation with findings. Type the note (see code audit) and turn silent drops into validation failures.

### 2.9 `attempts` is always 1 (LOW)

Every job hardcodes `attempts=1`, so "after repeated failure, mark blocked" and the `attempts: 3` shown in spec payloads are fiction. Either increment from the prior artifact or remove the field.

## 3. Cost (LLM usage)

What already works well: `provider: mock` is the default; MiniMax is documented as the dev provider and Anthropic as production; tests never touch a live LLM; every job skips on matching input hash; contexts are bounded to segment/paragraph scope; `normalize_gloss_reuse` deterministically dedupes glosses the model failed to reuse.

### 3.1 No per-job model routing (HIGH)

`ModelsConfig` holds one active provider+model for the whole pipeline. The model-strategy doc requires the opposite: strong model for content decisions and reviews, cheaper models only for non-authoritative drafting. Today the choice is all-or-nothing, so a production run pays Opus prices for every mechanical call, and a dev run reviews with the same cheap model that drafted. Recommend `models.roles: {draft: …, review: …, structure: …}` with dev/prod profiles (`.wenyan/config.yaml` override already exists). This also enables 2.6.

### 3.2 Candidate-gloss context grows linearly with document progress (MEDIUM)

`load_candidate_glosses` re-reads every prior segment's gloss artifact on each call (O(n²) file reads over a document) and the gloss job serializes the **entire document glossary so far** into every prompt — for a long document this dominates token cost. Filter candidates to entries whose surface appears among the segment's token surfaces before rendering the prompt; the glossary draft index already exists to support this.

### 3.3 Review prompts re-send full artifacts (LOW)

Review calls embed tokenization + glosses + candidate glossary + local context as raw JSON, and the system prompt embeds the full JSON schema. Fine at segment scale; combined-review (1.1) and candidate filtering (3.2) are the meaningful levers. Also consider dropping the "echo SEGMENT_ID / INPUT_HASH" prompt plumbing — the code overwrites those fields after parsing anyway, so requiring the model to echo them only adds failure modes.

### 3.4 Deterministic pre-checks save review calls (MEDIUM)

Implementing 2.2 means a mechanically broken tokenization fails locally instead of consuming a review call, and an approved review is never wasted on output that assembly will reject later.

## 4. Editor workflow and ease of use

- The ordinal-based addressing (`--chapter 1 --paragraph 2 --segment 3`) shared across status/jobs/skills is genuinely good UX, and delete-to-reject with status derived from disk is simple and predictable.
- `run` halting at the context stub on every segment makes the "chain a larger run" flow noisier than the docs suggest; `run --until-context` semantics (complete everything before context, then stop cleanly) would match actual practice better than a `not-implemented` failure exit.
- Spec drift to fix in docs: `--concurrency` and `--continue-on-blocked` are specced but unimplemented (concurrency config is loaded and never used); `review-paragraph-structure` / `review-report` are stubs (1.2); `validate-artifacts` overpromises (2.4). Either implement or trim the spec — the CLI spec is otherwise accurate and the golden-file status tests keep it honest.
- The three skills are well-structured and correctly scoped (mechanical steps in CLI, research in skills). The `inputHash` recipe in `drafting-context-notes` (shasum of raw file bytes) couples the skill to the exact serialization the store writes; it works today but will silently break status if serialization changes — another reason for hash-based staleness checks in status (2.3).

## 5. Recommended priority order

1. Deterministic segment reconstruction check in `split-segments` (2.1).
2. Deterministic tokenization offset/coverage validation (2.2).
3. Per-role model routing with dev/prod profiles (3.1, enables 2.6).
4. Merge the three CLI review passes into one segment review (1.1).
5. Hash-based staleness for segment reviews in status; fix rejected-review skip (2.3).
6. Real `validate-artifacts` or trimmed spec (2.4).
7. Candidate-gloss filtering (3.2); glossary merge moved out of review (2.7).
8. Prompt-version/hash in input hashes (2.5); doc cleanup for stubs and unimplemented flags (1.2, 4).
