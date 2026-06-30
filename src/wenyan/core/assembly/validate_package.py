from __future__ import annotations

from collections.abc import Sequence

from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.validation import CheckResult
from wenyan_models.reader.paragraph import ParagraphPackage

from wenyan.core.assembly.input_hash import assembly_input_hash, segment_output_hash
from wenyan.core.assembly.load_segment_outputs import CompiledSegmentInputs


def validate_paragraph_package(
    draft: ParagraphDraft,
    outputs: Sequence[CompiledSegmentInputs],
    package: ParagraphPackage,
) -> ParagraphAssemblyValidationArtifact:
    checks: list[CheckResult] = []
    outputs_by_id = {output.segment_id: output for output in outputs}
    draft_segment_ids = tuple(segment.id for segment in draft.segments)
    package_segment_ids = tuple(segment.id for segment in package.segments)
    output_segment_ids = tuple(
        output.segment_id
        for draft_segment in draft.segments
        if (output := outputs_by_id.get(draft_segment.id)) is not None
    )

    if package_segment_ids != draft_segment_ids:
        checks.append(
            CheckResult(
                code="segment-order",
                message="package segment ids do not match draft order",
            )
        )
    if output_segment_ids != draft_segment_ids:
        checks.append(
            CheckResult(
                code="segment-order",
                message="output segment ids do not match draft order",
            )
        )

    draft_texts = "".join(segment.text for segment in draft.segments)
    package_texts = "".join(segment.text for segment in package.segments)
    if package_texts != draft_texts:
        checks.append(
            CheckResult(
                code="segment-reconstruction",
                message="concatenated segment texts do not match draft",
            )
        )

    for draft_segment in draft.segments:
        output = outputs_by_id.get(draft_segment.id)
        if output is None:
            continue
        gloss_by_token = {
            decision.token_id: decision.gloss_id for decision in output.glosses.gloss_decisions
        }
        for token in output.tokenization.tokens:
            gloss_id = gloss_by_token.get(token.id, "")
            if not gloss_id:
                checks.append(
                    CheckResult(
                        code="token-gloss-coverage",
                        message=f"token {token.id} has no gloss decision",
                    )
                )

    for segment in package.segments:
        token_ids = {token.id for token in segment.tokens}
        if len(token_ids) != len(segment.tokens):
            checks.append(
                CheckResult(
                    code="unique-token-ids",
                    message=f"duplicate token ids in segment {segment.id}",
                )
            )
        for note in segment.notes:
            for anchor_token_id in note.anchor_token_ids:
                if anchor_token_id not in token_ids:
                    checks.append(
                        CheckResult(
                            code="note-anchors",
                            message=(
                                f"note {note.id} anchors missing token {anchor_token_id}"
                            ),
                        )
                    )

    segment_hashes = {
        str(output.segment_id): segment_output_hash(output) for output in outputs
    }
    status = ValidationStatus.PASSED if not checks else ValidationStatus.FAILED
    return ParagraphAssemblyValidationArtifact(
        paragraph_id=draft.paragraph_id,
        input_hash=assembly_input_hash(draft, segment_hashes),
        status=status,
        checks=tuple(checks),
    )
