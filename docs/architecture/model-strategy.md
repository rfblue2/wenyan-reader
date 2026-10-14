# Model Strategy

## Runtime Boundary

Use high-quality cloud LLMs during preprocessing only. The reader app should never call an LLM at runtime.

## Default Model Choice

- Primary content model: the strongest available Claude Opus model at implementation time. Based on current public benchmarking for Classical Chinese tasks, use `Claude Opus 4.8` as the target default if available.
- Long-context support model: use Gemini Pro-class long-context models when a task genuinely needs large surrounding context, such as chapter-level summarization or source synthesis.
- Cost fallback: reserve cheaper models for non-authoritative drafting only, never for final review and quality jobs.

The pipeline should hide provider details behind a model adapter so the exact model can be changed without rewriting preprocessing logic.

## Model Routing

Use the primary content model for:

- Chapter and paragraph discovery.
- Segmentation review.
- Classical Chinese tokenization decisions.
- Contextual gloss sense selection.
- New gloss drafting.
- Grammar notes.
- Context notes.
- Review and quality jobs.

Use deterministic code for:

- Normalization.
- UUID generation.
- Source hashes and input hashes.
- Offset validation.
- Schema validation.
- Path validation.
- Packaging.
- Retry and cache bookkeeping.

Use deterministic dictionaries or lexicons before LLM calls when they can reduce cost without reducing quality.

Use long-context models only for summarizing larger context windows or synthesizing source material, not for processing an entire large document in one paragraph job or focused segment subjob.

## LLM Call Contracts

Every LLM call should request strict structured output.

The output schema should include whichever fields are relevant to the call:

- Proposed chapter or paragraph spans.
- Proposed reader segments.
- Token occurrences with offsets.
- Gloss reuse or new gloss proposals.
- New glosses with pinyin.
- Notes with anchors and sources.
- Review findings.

The parser should reject malformed output. The command may exit non-zero so the editor can rerun; structural validation remains deterministic.
