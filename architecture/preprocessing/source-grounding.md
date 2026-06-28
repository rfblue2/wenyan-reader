# Source Grounding

## Purpose

Context-note generation should use retrieval where possible.

Source material may include:

- The source passage itself.
- Existing translations.
- Commentaries.
- Historical reference texts.
- Editor-provided notes.
- Local curated source excerpts.

The relevant paragraph job or focused segment subjob should pass source snippets with stable source IDs. Context notes should cite source IDs in their `sources` metadata when a claim depends on external grounding.

If no source supports a claim, the model should either omit the note or mark it as unsupported in the review report rather than inventing a citation.

## Review Handoff

Source grounding feeds the review and quality jobs, but it is not itself the full QA process. Grounded source snippets should be passed into any review job that needs to assess context notes, source support, or cross-document consistency.

See [Review And Quality Jobs](review-and-quality-jobs.md) for the concrete validation, review, and blocking jobs.
