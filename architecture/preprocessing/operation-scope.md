# Operation Scope

## Source Unit

The source input is always a full document. A source should not be modeled as a chapter excerpt or paragraph excerpt, even if the pipeline later processes it in smaller jobs.

Large documents must still be processable in small units, down to individual text segments for content generation. The pipeline should therefore split the full document into an intermediate chapter, paragraph, and segment structure before generating reader content.

Chapter, paragraph, and segment boundaries are content decisions and should usually be proposed by an LLM. Deterministic code should validate that the proposed spans reconstruct the full document exactly, but it should not decide literary or pedagogical boundaries.

## Document-Level Operations

- Ingest the source as one complete document.
- Normalize encoding and canonical text representation.
- Create a stable document ID and source text hash.
- Ask the LLM to propose top-level chapter boundaries, using any source headings as evidence.
- Validate that chapter spans reconstruct the full document exactly.
- Maintain the document-level glossary index (`indexes/glossary-draft.json` during preprocessing; promoted to `content/documents/<document-id>/glosses/index.json` at package time).
- Maintain document-level entity and term indexes under `indexes/`.
- Build final `document.json` and `glosses/index.json`.

## Chapter-Level Operations

- Ask the LLM to propose paragraph boundaries within a chapter.
- Generate or update a chapter summary used as context for paragraph structure jobs and focused segment subjobs.
- Extract chapter-local people, places, titles, and recurring terms.
- Validate that paragraph spans reconstruct the chapter text exactly.
- Build final `chapter.json`.

## Paragraph-Level Operations

- Build a bounded prompt context for one paragraph.
- Segment the paragraph into reader text segments.
- Draft context notes only when the note applies across multiple segments or needs paragraph-level framing.
- Prepare resumable segment subjobs with the smallest context needed for each focused task.
- Validate that segment text reconstructs the paragraph text.
- Write the paragraph container after required segment subjobs complete.

## Segment-Level Operations

- Build a bounded prompt context for one segment.
- Tokenize the segment.
- Select existing glosses or propose new glosses.
- Draft grammar notes.
- Draft context notes that apply only to that segment.
- Validate segment text and token offsets.
- Validate note anchors within the segment.
- Compute or verify `newGlossIds`.
- Check that every glossable unit in the segment is covered.
- Run focused review and quality jobs for tokenization, glosses, grammar notes, and segment-local context notes.

This division keeps expensive gloss, grammar, and tokenization calls scoped to the smallest useful unit. Paragraph-level processing may spend more context tokens to understand paragraph flow, but it should not perform operations that can be done accurately at segment scope.
