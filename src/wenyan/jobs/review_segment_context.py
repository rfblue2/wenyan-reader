import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    paragraph_draft_ref,
    segment_context_notes_ref,
    segment_context_review_ref,
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    ContextReviewArtifact,
    GlossesArtifact,
    SegmentInput,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped


def run_review_segment_context(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[ContextReviewArtifact]:
    context_ref = segment_context_notes_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(context_ref):
        return JobFailure(code="missing-input", message="context notes artifact is missing")
    context_notes = ctx.artifacts.read(context_ref, ContextNotesArtifact)
    input_ref = segment_input_ref(document_id, segment_id_value)
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(
            code="missing-input",
            message="segment input and tokenization are required for context review",
        )
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    review_ref = segment_context_review_ref(document_id, segment_id_value)
    input_hash = sha256_text(context_notes.model_dump_json(by_alias=True))
    if ctx.artifacts.exists(review_ref) and not options.force:
        existing = ctx.artifacts.read(review_ref, ContextReviewArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="context review is current")
    glosses_json = "null"
    glosses_ref = segment_glosses_ref(document_id, segment_id_value)
    if ctx.artifacts.exists(glosses_ref):
        glosses = ctx.artifacts.read(glosses_ref, GlossesArtifact)
        glosses_json = glosses.model_dump_json(by_alias=True)
    paragraph_context_notes_json = "[]"
    draft_ref = paragraph_draft_ref(document_id, segment_input.paragraph_id)
    if ctx.artifacts.exists(draft_ref):
        draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
        paragraph_context_notes_json = json.dumps(
            [item for item in draft.paragraph_context_notes],
            ensure_ascii=False,
        )
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-context-review",
    )
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "segment_text": segment_input.segment_text,
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "context_notes_json": context_notes.model_dump_json(by_alias=True),
        "glosses_json": glosses_json,
        "local_context_json": json.dumps(segment_input.local_context, ensure_ascii=False),
        "source_snippets_json": json.dumps(
            [item for item in segment_input.source_snippets],
            ensure_ascii=False,
        ),
        "paragraph_context_notes_json": paragraph_context_notes_json,
    }
    review = ctx.llm.complete_model(RenderedPrompt(template, context), ContextReviewArtifact)
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
        return JobFailure(code="review-rejected", message="context review rejected")
    return Promoted(artifact=review)
