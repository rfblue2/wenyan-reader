import json

from wenyan.core.gloss.filter_candidates import filter_candidates_by_token_surfaces
from wenyan.core.gloss.glossary_draft import (
    load_candidate_glosses,
    load_glossary_draft,
    merge_approved_glosses,
    save_glossary_draft,
)
from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.run.segment_pipeline import GLOSS_STAGE
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import Prepared, SegmentReviewJobSpec, run_segment_job
from wenyan_models.artifacts.segment import GlossesArtifact, SegmentInput, SegmentReview, TokenizationArtifact
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_gloss_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | Prepared:
    glosses_ref = SegmentRef(SegmentArtifactKind.GLOSSES, document_id, segment_id_value)
    if not ctx.artifacts.exists(glosses_ref):
        return JobFailure(code="missing-input", message="glosses artifact is missing")
    glosses = ctx.artifacts.read(glosses_ref, GlossesArtifact)
    input_ref = SegmentRef(SegmentArtifactKind.INPUT, document_id, segment_id_value)
    tokenization_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(
            code="missing-input",
            message="segment input and tokenization are required for gloss review",
        )
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    input_hash = sha256_text(glosses.model_dump_json(by_alias=True))
    all_candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    prompt_candidates = filter_candidates_by_token_surfaces(all_candidates, tokenization)
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "segment_text": segment_input.segment_text,
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "glosses_json": glosses.model_dump_json(by_alias=True),
        "candidate_glosses_json": json.dumps(
            [entry.model_dump(by_alias=True) for entry in prompt_candidates],
            ensure_ascii=False,
        ),
    }
    return Prepared(input_hash, context)


def _merge_glossary_after_gloss_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> None:
    glosses = ctx.artifacts.read(
        SegmentRef(SegmentArtifactKind.GLOSSES, document_id, segment_id_value),
        GlossesArtifact,
    )
    draft = merge_approved_glosses(load_glossary_draft(ctx.artifacts, document_id), glosses)
    save_glossary_draft(ctx.artifacts, document_id, draft, dry_run=False)


_GLOSS_REVIEW_SPEC = SegmentReviewJobSpec(
    stage=GLOSS_STAGE,
    prompt_name="segment-gloss-review",
    prepare=_prepare_gloss_review,
    post_write=_merge_glossary_after_gloss_review,
    empty_message="no segments to review",
    skip_reason="gloss review is current",
    reject_message="gloss review rejected",
)


def run_review_segment_gloss(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[SegmentReview]:
    return run_segment_job(ctx, document_id, target, options, _GLOSS_REVIEW_SPEC)
