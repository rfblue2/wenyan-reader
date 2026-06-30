from collections.abc import Mapping

from wenyan_models.artifacts.package import PackageValidationArtifact
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import ChapterId, ContentHash, ParagraphId
from wenyan_models.domain.validation import CheckResult
from wenyan_models.reader.document import ChapterPackage, DocumentManifest, GlossIndex
from wenyan_models.reader.paragraph import ParagraphPackage

from wenyan.core.package.collect import ReadyParagraph


def validate_document_package(
    *,
    manifest: DocumentManifest,
    gloss_index: GlossIndex,
    chapter_packages: Mapping[ChapterId, ChapterPackage],
    paragraph_index: Mapping[ParagraphId, ReadyParagraph],
    input_hash: ContentHash,
    paragraphs_packaged: int,
) -> PackageValidationArtifact:
    checks: list[CheckResult] = []
    gloss_ids = {entry.id for entry in gloss_index.glosses}

    if paragraphs_packaged == 0:
        checks.append(CheckResult(code="empty-package", message="no paragraphs to package"))

    if not manifest.chapters:
        checks.append(CheckResult(code="chapter-count", message="document has no chapters"))

    chapter_ids = [chapter.id for chapter in manifest.chapters]
    if len(chapter_ids) != len(set(chapter_ids)):
        checks.append(CheckResult(code="unique-chapter-ids", message="duplicate chapter ids"))

    all_paragraph_ids: list[ParagraphId] = []
    for chapter_nav in manifest.chapters:
        chapter = chapter_packages.get(chapter_nav.id)
        if chapter is None:
            checks.append(
                CheckResult(
                    code="chapter-reachability",
                    message=f"chapter {chapter_nav.id} is missing from package",
                ),
            )
            continue
        if chapter_nav.path != f"chapters/{chapter_nav.id}/chapter.json":
            checks.append(
                CheckResult(
                    code="chapter-path",
                    message=f"chapter {chapter_nav.id} has unexpected manifest path",
                ),
            )
        if not chapter.paragraphs:
            checks.append(
                CheckResult(
                    code="paragraph-count",
                    message=f"chapter {chapter_nav.id} has no paragraphs",
                ),
            )
        paragraph_ids = [paragraph.id for paragraph in chapter.paragraphs]
        if len(paragraph_ids) != len(set(paragraph_ids)):
            checks.append(
                CheckResult(
                    code="unique-paragraph-ids",
                    message=f"duplicate paragraph ids in chapter {chapter_nav.id}",
                ),
            )
        all_paragraph_ids.extend(paragraph_ids)
        for paragraph_nav in chapter.paragraphs:
            expected_path = f"paragraphs/{paragraph_nav.id}.json"
            if paragraph_nav.path != expected_path:
                checks.append(
                    CheckResult(
                        code="paragraph-path",
                        message=f"paragraph {paragraph_nav.id} has unexpected manifest path",
                    ),
                )
            ready = paragraph_index.get(paragraph_nav.id)
            if ready is None:
                checks.append(
                    CheckResult(
                        code="paragraph-reachability",
                        message=f"paragraph {paragraph_nav.id} is missing from package",
                    ),
                )
                continue
            _validate_paragraph_glosses_and_notes(
                checks,
                ready.package,
                gloss_ids,
            )

    if len(all_paragraph_ids) != len(set(all_paragraph_ids)):
        checks.append(
            CheckResult(code="unique-paragraph-ids", message="duplicate paragraph ids in document"),
        )

    status = ValidationStatus.PASSED if not checks else ValidationStatus.FAILED
    return PackageValidationArtifact(
        input_hash=input_hash,
        status=status,
        checks=tuple(checks),
        paragraphs_packaged=paragraphs_packaged,
    )


def _validate_paragraph_glosses_and_notes(
    checks: list[CheckResult],
    package: ParagraphPackage,
    gloss_ids: set[str],
) -> None:
    for segment in package.segments:
        token_ids = {token.id for token in segment.tokens}
        for token in segment.tokens:
            if token.gloss_id not in gloss_ids:
                checks.append(
                    CheckResult(
                        code="token-gloss-reference",
                        message=f"token {token.id} references missing gloss {token.gloss_id}",
                    ),
                )
        for gloss_id in segment.new_gloss_ids:
            if gloss_id not in gloss_ids:
                checks.append(
                    CheckResult(
                        code="new-gloss-reference",
                        message=f"segment {segment.id} references missing new gloss {gloss_id}",
                    ),
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
                        ),
                    )
