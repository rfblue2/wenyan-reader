# Pipeline Stages

## Source Normalization

Scope: full document.

LLM use: none.

Prepare the source text for annotation while preserving the text that the reader will display.

Responsibilities:

- Normalize file encoding.
- Decide punctuation handling.
- Preserve the canonical displayed segment string.
- Avoid silently changing the Classical Chinese text during later stages.

## Structure Discovery

Scope: full document for chapter discovery, then chapter level for paragraph discovery.

LLM use: yes.

The source is always a full document, but chapter and paragraph units should usually be decided by the LLM. If the raw source contains obvious headings or paragraph breaks, those should be supplied to the model as evidence rather than treated as unquestionable structure.

The model should propose chapter and paragraph spans. Deterministic validation should then check that:

- Spans are ordered.
- Spans do not overlap.
- Spans do not omit text.
- Span text reconstructs the normalized document or chapter exactly.
- Proposed IDs are stable for unchanged spans when possible.

Responsibilities:

- Preserve original text order.
- Assign UUIDs to chapters and paragraphs.
- Write initial chapter and paragraph structure proposals.
- Allow a single paragraph to be reprocessed without changing stable IDs elsewhere.

## Segmentation

Scope: paragraph.

LLM use: yes, bounded to one paragraph at a time.

Split the paragraph into bite-sized reading segments. Segments should usually be one sentence or a small pair of tightly connected sentences. The goal is pedagogical readability, not mechanical sentence splitting.

Deterministic validation should verify that segment strings concatenate back to the paragraph text, modulo explicitly allowed paragraph separators.

Once segment boundaries are accepted, each segment becomes a container for focused resumable subjobs: tokenization, glossing, grammar annotation, context annotation, and focused review. A paragraph may be partially processed while some segment subjobs have succeeded and others remain pending, failed, or blocked.

## Tokenization

Scope: segment.

LLM use: yes.

Identify glossable units within each segment.

Most tokens will be single characters, but tokenization must support n-grams for:

- Names.
- Places.
- Titles.
- Idioms.
- Fixed expressions.
- Multi-character words.
- Contextual phrases that should be glossed as a unit.

Each token occurrence receives offsets into the segment text and later points to a document-level `glossId`.

## Gloss Drafting

Scope: segment for local sense selection; full document for glossary aggregation.

LLM use: yes.

Create or reuse document-level gloss entries.

Recommended priority:

- Reuse an existing gloss entry when the same sense has already appeared.
- Use deterministic dictionaries or curated lexicons when available.
- Use LLM assistance for unresolved or context-sensitive cases.
- Create separate gloss entries for distinct senses of the same surface form.

Each gloss must include:

- Surface form.
- Pinyin.
- English gloss.

For each token occurrence, the model should decide whether it uses an existing `glossId` or requires a new gloss entry. This handles homonyms and polysemy.

The model must justify new gloss entries internally in intermediate output, but the final reader package should store only the fields required by the storage format unless review metadata is intentionally preserved.

## Note Drafting

Scope: segment by default; paragraph only for cross-segment context notes.

LLM use: yes, with source grounding for context notes.

Create grammar and context notes only when useful to comprehension.

Grammar notes should be drafted at segment scope. They should explain salient Classical Chinese constructions in the anchored text without paying for paragraph-level context unless the construction truly depends on a larger span.

Context notes should explain information needed to understand the passage, such as:

- People.
- Places.
- Historical setting.
- Literary references.
- Common scholarly interpretation.
- Clarifying information that an English-speaking learner is unlikely to know.

Context notes may be drafted at paragraph scope when the note applies across multiple text segments or requires paragraph-level framing. Segment-local context notes should be drafted at segment scope.

For context notes, the model should not rely only on memory. The relevant job should provide source snippets or reference material when available, and the model should cite those source IDs in note metadata.

## Structural Validation

Scope: segment, paragraph, chapter, or full document depending on the check.

LLM use: none.

Validation should check:

- File paths.
- JSON shape.
- UUID format.
- Token offsets.
- Token coverage.
- Gloss references.
- Note anchors.
- Reachability from `document.json`.

## Review And Quality Jobs

Scope: segment for tokenization, glosses, and grammar; paragraph only for paragraph-level context notes and paragraph reconstruction checks.

LLM use: yes.

Since first-stage content review will be LLM-based rather than mandatory human review, QA should be a separate pass from drafting.

It should check:

- The selected gloss is correct in the local segment context.
- Homonyms and polysemous words are disambiguated correctly.
- Pinyin is accurate.
- Grammar notes describe the construction actually present.
- Context notes are not hallucinated.
- Context notes are grounded in real sources.
- Recurring people, places, and interpretive claims are consistent across the document.

See [Review And Quality Jobs](review-and-quality-jobs.md) for the concrete validation and review job definitions.
