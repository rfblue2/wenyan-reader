from __future__ import annotations

from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.ids import ContentHash
from wenyan_models.domain.validation import CheckResult, validation_status
from wenyan_models.reader.paragraph import ParagraphPackage


def validate_paragraph_package(
    draft: ParagraphDraft,
    package: ParagraphPackage,
    *,
    input_hash: ContentHash,
) -> ParagraphAssemblyValidationArtifact:
    checks: list[CheckResult] = []

    draft_texts = "".join(segment.text for segment in draft.segments)
    package_texts = "".join(segment.text for segment in package.segments)
    if package_texts != draft_texts:
        checks.append(
            CheckResult(
                code="segment-reconstruction",
                message="concatenated segment texts do not match draft",
            )
        )

    for segment in package.segments:
        for token in segment.tokens:
            if not token.gloss_id:
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

    return ParagraphAssemblyValidationArtifact(
        paragraphId=draft.paragraph_id,
        inputHash=input_hash,
        status=validation_status(checks),
        checks=tuple(checks),
    )
