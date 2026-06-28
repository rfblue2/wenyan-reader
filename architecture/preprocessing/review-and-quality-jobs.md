# Review And Quality Jobs

## Purpose

Define the review, validation, and blocking jobs used by the preprocessing pipeline.

Quality checks should be explicit jobs, not hidden inside drafting calls. Deterministic validation proves that artifacts are structurally sound. LLM review checks editorial correctness, source support, and Classical Chinese interpretation.

## Job Principles

- Use deterministic code for shape, path, hash, offset, anchor, reconstruction, and reachability checks.
- Use LLM review for content judgments: gloss sense, pinyin, grammar explanation, segmentation quality, and source-grounded context.
- Keep review scoped to the smallest useful unit. Segment review should be split into focused review subjobs whenever tokenization, glossing, grammar, or context can be checked independently.
- Mark the smallest affected unit as blocked after review rejection.
- Preserve review reports as intermediate artifacts so failures are auditable and prompts can be improved.

## Deterministic Validation Jobs

### Chapter Span Validation

Scope: document-level chapter proposal.

Inputs:

- `normalized-document.json`
- `chapter-proposal.json`

Checks:

- Chapter spans are ordered.
- Chapter spans do not overlap.
- Chapter spans do not omit text.
- Chapter span text reconstructs the normalized document exactly.
- Chapter IDs are stable for unchanged spans when possible.

Output:

- `structure/chapter-proposal.validation.json`

### Paragraph Span Validation

Scope: chapter-level paragraph proposal.

Inputs:

- Chapter text from the normalized document.
- `structure/chapters/chapter-id/paragraph-proposal.json`

Checks:

- Paragraph spans are ordered.
- Paragraph spans do not overlap.
- Paragraph spans do not omit text.
- Paragraph span text reconstructs the chapter exactly.
- Paragraph IDs are stable for unchanged spans when possible.

Output:

- `structure/chapters/chapter-id/paragraph-proposal.validation.json`

### Segment Reconstruction Validation

Scope: paragraph structure job.

Inputs:

- Paragraph text.
- `jobs/paragraphs/paragraph-id/draft.json`

Checks:

- Segment strings are ordered.
- Segment strings concatenate back to the paragraph text, modulo explicitly allowed paragraph separators.
- Segment IDs are unique within the paragraph.
- Paragraph-level context note anchors point to existing segment IDs.
- Source IDs referenced by paragraph-level context notes exist in the job input.

Output:

- `jobs/paragraphs/paragraph-id/validation.json`

### Segment Output Validation

Scope: segment subjobs during `assemble-paragraph`.

Inputs:

- `jobs/segments/segment-id/input.json`
- Accepted segment subjob outputs for the segment.

Checks:

- Segment text matches the segment subjob input.
- Token offsets match the segment text.
- Token IDs are unique within the segment.
- Token coverage satisfies the configured policy.
- Every token references an existing candidate gloss or newly proposed gloss.
- Every new gloss has required fields.
- Note anchors reference tokens in the same segment.
- Source IDs referenced by segment-local context notes exist in the job input.

### Paragraph Package Validation

Scope: paragraph assembly job.

Inputs:

- Paragraph structure draft.
- Completed segment subjob outputs for the paragraph.
- Assembled paragraph package.

Checks:

- All required segment subjob outputs are present or intentionally blocked.
- Segment order matches the paragraph structure draft.
- Segment texts reconstruct the paragraph.
- Segment notes, tokens, and new gloss IDs satisfy the final storage schema.
- Paragraph package is reachable from the chapter manifest.

Output:

- `jobs/assembly/paragraph-id/validation.json`

### Document Package Validation

Scope: final package.

Inputs:

- `document.json`
- `glosses/index.json`
- `chapters/*/chapter.json`
- `chapters/*/paragraphs/*.json`

Checks:

- All referenced paths exist.
- All IDs are unique within their scope.
- Every token points to an existing gloss.
- Every note anchors to tokens in the same segment.
- All chapters, paragraphs, and segments are reachable from `document.json`.

Output:

- `jobs/package/validation.json`

Runs as part of `package-document`.

## LLM Review Jobs

### Paragraph Structure Review

Scope: paragraph structure job (`review-paragraph-structure`).

Inputs:

- Original paragraph.
- Neighboring paragraph window.
- Chapter title and chapter summary.
- Proposed segment boundaries.
- Optional paragraph-level context notes.
- Relevant source snippets for paragraph-level context notes.

Review checklist:

- Segment boundaries are pedagogically useful and do not split tightly coupled text badly.
- Segment boundaries preserve the full paragraph text.
- Paragraph-level context notes really need paragraph-level framing.
- Context notes avoid unsupported claims and cite source IDs where needed.
- Anchors point to the right segment IDs.

Output:

- `jobs/paragraphs/paragraph-id/review.json`

Failure behavior:

- Write `jobs/paragraphs/paragraph-id/review.json` with findings and required fixes.
- Exit non-zero on rejection; mark the paragraph structure component blocked in status.

### Segment Tokenization Review

Scope: `tokenize-segment` job.

Inputs:

- Original segment.
- Minimal local context needed to interpret the segment.
- Produced token surfaces and offsets.

Review checklist:

- Tokenization identifies the intended glossable units.
- No token is punctuation or whitespace only.
- **Single-character tokens are preferred** for ordinary words and particles; reject overly coarse phrase tokens (for example `國之大事` instead of `國` / `之` / `大事`).
- Multi-character tokens are appropriate only for names, titles, places, and fixed compounds (`孫子`, `大事`, `死生`, `存亡`, `兵者` in topic use).
- Token boundaries are pedagogically useful.
- Multi-character names, places, idioms, titles, and fixed expressions are not split incorrectly.
- Offsets preserve the original segment text.

Failure behavior:

- Write the review artifact with findings and required fixes.
- Exit non-zero on rejection; block only the tokenization subjob.

### Segment Gloss Review

Scope: `gloss-segment` job.

Inputs:

- Original segment.
- Reviewed tokenization output.
- Candidate glossary entries.
- Produced gloss decisions and new gloss entries.

Review checklist:

- Gloss sense selection is correct in the local context.
- Homonyms and polysemous words are disambiguated correctly; **pinyin matches the contextual reading** (tone included), not merely a default homograph reading.
- Pinyin is accurate for the chosen sense.
- New glosses are necessary and not duplicates of existing entries.

Failure behavior:

- Write the review artifact with findings and required fixes.
- Exit non-zero on rejection; block only the gloss subjob.

### Segment Grammar Review

Scope: `annotate-segment-grammar` job.

Inputs:

- Original segment.
- Reviewed tokenization and gloss outputs.
- Produced grammar notes.

Review checklist:

- Grammar notes describe constructions actually present in the segment.
- Grammar notes are anchored to the right tokens.
- Grammar notes are useful for comprehension rather than generic explanation.
- Grammar notes do not conflict with selected gloss senses.

Failure behavior:

- Write the review artifact with findings and required fixes.
- Exit non-zero on rejection; block only the grammar subjob.

### Segment Context Review

Scope: `annotate-segment-context` job.

Inputs:

- Original segment.
- Minimal local context needed to interpret the segment.
- Reviewed tokenization and gloss outputs.
- Produced segment-local context notes.
- Relevant source snippets for segment-local context notes.

Review checklist:

- Context notes are useful and anchored correctly.
- Context notes are source-grounded when they make factual or interpretive claims.
- Context notes avoid unsupported historical, literary, or biographical claims.
- Context notes do not duplicate paragraph-level context notes.

Failure behavior:

- Write the review artifact with findings and required fixes.
- Exit non-zero on rejection; block only the context subjob.

### Paragraph Package Review

Scope: paragraph assembly job.

Inputs:

- Original paragraph.
- Paragraph structure draft.
- Completed segment outputs.
- Assembled paragraph package.

Review checklist:

- The assembled paragraph still reads as the original paragraph.
- Segment outputs are internally consistent when read together.
- Paragraph-level context notes do not duplicate or conflict with segment-local notes.
- New gloss introductions are pedagogically sensible in paragraph context.

Failure behavior:

- Write `jobs/assembly/paragraph-id/review.json` with findings.
- Exit non-zero on rejection; prefer blocking the specific segment or paragraph-level note that caused the failure.

### Document Consistency Review

Scope: document-level index and final package. Runs as part of `package-document`.

Inputs:

- Document-level entity and term indexes.
- Glossary index.
- Completed chapters and paragraphs.
- Prior review findings.

Review checklist:

- Recurring people, places, titles, and interpretive claims are consistent across the document.
- Gloss entries are not duplicated for the same surface and sense.
- Distinct senses of the same surface form have distinct gloss entries.
- Newly introduced glosses appear at their first canonical occurrence in document order.
- Source-grounded claims use consistent source references.

Failure behavior:

- Produce targeted reruns for affected segments, paragraph notes, or glossary entries.
- Do not rewrite the whole document when only a segment or glossary entry is affected.

## Blocking

Review or validation failure should mark the smallest affected unit as blocked. A blocked segment subjob should not prevent completed sibling segments from remaining usable, though it can prevent final paragraph packaging until the block is resolved.

Blocked state is reflected in status and in the component's review artifact. The editor resolves blocks by fixing inputs, deleting rejected artifacts, or rerunning the focused command.
