import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    segment_grammar_notes_ref,
    segment_grammar_review_ref,
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.segment import (
    GlossesArtifact,
    GrammarNotesArtifact,
    GrammarReviewArtifact,
    SegmentInput,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped


def run_review_segment_grammar(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GrammarReviewArtifact]:
    grammar_ref = segment_grammar_notes_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(grammar_ref):
        return JobFailure(code="missing-input", message="grammar notes artifact is missing")
    grammar_notes = ctx.artifacts.read(grammar_ref, GrammarNotesArtifact)
    input_ref = segment_input_ref(document_id, segment_id_value)
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(
            code="missing-input",
            message="segment input and tokenization are required for grammar review",
        )
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    review_ref = segment_grammar_review_ref(document_id, segment_id_value)
    input_hash = sha256_text(grammar_notes.model_dump_json(by_alias=True))
    if ctx.artifacts.exists(review_ref) and not options.force:
        existing = ctx.artifacts.read(review_ref, GrammarReviewArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="grammar review is current")
    glosses_json = "null"
    glosses_ref = segment_glosses_ref(document_id, segment_id_value)
    if ctx.artifacts.exists(glosses_ref):
        glosses = ctx.artifacts.read(glosses_ref, GlossesArtifact)
        glosses_json = glosses.model_dump_json(by_alias=True)
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-grammar-review",
    )
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "segment_text": segment_input.segment_text,
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "grammar_notes_json": grammar_notes.model_dump_json(by_alias=True),
        "glosses_json": glosses_json,
        "local_context_json": json.dumps(segment_input.local_context, ensure_ascii=False),
    }
    review = ctx.llm.complete_model(RenderedPrompt(template, context), GrammarReviewArtifact)
    review = review.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    if options.dry_run:
        return Promoted(artifact=review)
    ctx.artifacts.write(review_ref, review, dry_run=False)
    if review.status == ReviewStatus.REJECTED:
        return JobFailure(code="review-rejected", message="grammar review rejected")
    return Promoted(artifact=review)
