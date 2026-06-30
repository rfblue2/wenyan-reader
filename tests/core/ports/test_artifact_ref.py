from pathlib import Path

import pytest

from wenyan.core.adapters.paths import artifact_path
from wenyan.core.ports import artifact_ref as refs
from wenyan.core.ports.artifact_ref import _make_ref
from wenyan_models.domain.enums import ArtifactKind
from wenyan_models.domain.ids import (
    chapter_id,
    document_id,
    paragraph_id,
    segment_id,
)

DOC = document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")
CHAPTER = chapter_id("6c708ee9-95c0-4d23-8a4f-8cb5fd62c605")
PARAGRAPH = paragraph_id("c777d984-afd6-4a31-aa34-2d26d29fb445")
SEGMENT = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")


@pytest.mark.parametrize(
    ("factory", "expected_kind"),
    [
        (lambda: refs.normalized_document_ref(DOC), ArtifactKind.NORMALIZED_DOCUMENT),
        (lambda: refs.chapter_proposal_ref(DOC), ArtifactKind.CHAPTER_PROPOSAL),
        (
            lambda: refs.chapter_proposal_validation_ref(DOC),
            ArtifactKind.CHAPTER_PROPOSAL_VALIDATION,
        ),
        (lambda: refs.chapter_summary_ref(DOC, CHAPTER), ArtifactKind.CHAPTER_SUMMARY),
        (lambda: refs.paragraph_proposal_ref(DOC, CHAPTER), ArtifactKind.PARAGRAPH_PROPOSAL),
        (
            lambda: refs.paragraph_proposal_validation_ref(DOC, CHAPTER),
            ArtifactKind.PARAGRAPH_PROPOSAL_VALIDATION,
        ),
        (lambda: refs.paragraph_draft_ref(DOC, PARAGRAPH), ArtifactKind.PARAGRAPH_DRAFT),
        (
            lambda: refs.paragraph_draft_validation_ref(DOC, PARAGRAPH),
            ArtifactKind.PARAGRAPH_DRAFT_VALIDATION,
        ),
        (
            lambda: refs.paragraph_draft_review_ref(DOC, PARAGRAPH),
            ArtifactKind.PARAGRAPH_DRAFT_REVIEW,
        ),
        (lambda: refs.segment_input_ref(DOC, SEGMENT), ArtifactKind.SEGMENT_INPUT),
        (lambda: refs.segment_tokenization_ref(DOC, SEGMENT), ArtifactKind.TOKENIZATION),
        (
            lambda: refs.segment_tokenization_review_ref(DOC, SEGMENT),
            ArtifactKind.TOKENIZATION_REVIEW,
        ),
        (lambda: refs.segment_glosses_ref(DOC, SEGMENT), ArtifactKind.GLOSSES),
        (lambda: refs.segment_gloss_review_ref(DOC, SEGMENT), ArtifactKind.GLOSS_REVIEW),
        (lambda: refs.segment_grammar_notes_ref(DOC, SEGMENT), ArtifactKind.GRAMMAR_NOTES),
        (lambda: refs.segment_grammar_review_ref(DOC, SEGMENT), ArtifactKind.GRAMMAR_REVIEW),
        (lambda: refs.segment_context_notes_ref(DOC, SEGMENT), ArtifactKind.CONTEXT_NOTES),
        (lambda: refs.segment_context_review_ref(DOC, SEGMENT), ArtifactKind.CONTEXT_REVIEW),
        (lambda: refs.entity_index_ref(DOC), ArtifactKind.ENTITY_INDEX),
        (lambda: refs.term_index_ref(DOC), ArtifactKind.TERM_INDEX),
        (lambda: refs.glossary_draft_ref(DOC), ArtifactKind.GLOSSARY_DRAFT),
        (
            lambda: refs.paragraph_assembly_package_ref(DOC, PARAGRAPH),
            ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE,
        ),
        (
            lambda: refs.paragraph_assembly_validation_ref(DOC, PARAGRAPH),
            ArtifactKind.PARAGRAPH_ASSEMBLY_VALIDATION,
        ),
        (
            lambda: refs.paragraph_assembly_review_ref(DOC, PARAGRAPH),
            ArtifactKind.PARAGRAPH_ASSEMBLY_REVIEW,
        ),
        (lambda: refs.package_validation_ref(DOC), ArtifactKind.PACKAGE_VALIDATION),
    ],
)
def test_each_artifact_kind_has_distinct_factory(
    factory: object,
    expected_kind: ArtifactKind,
) -> None:
    ref = factory()
    assert ref.kind == expected_kind
    assert ref.document_id == DOC


def test_all_kinds_are_covered() -> None:
    produced = {
        refs.normalized_document_ref(DOC).kind,
        refs.chapter_proposal_ref(DOC).kind,
        refs.chapter_proposal_validation_ref(DOC).kind,
        refs.chapter_summary_ref(DOC, CHAPTER).kind,
        refs.paragraph_proposal_ref(DOC, CHAPTER).kind,
        refs.paragraph_proposal_validation_ref(DOC, CHAPTER).kind,
        refs.paragraph_draft_ref(DOC, PARAGRAPH).kind,
        refs.paragraph_draft_validation_ref(DOC, PARAGRAPH).kind,
        refs.paragraph_draft_review_ref(DOC, PARAGRAPH).kind,
        refs.segment_input_ref(DOC, SEGMENT).kind,
        refs.segment_tokenization_ref(DOC, SEGMENT).kind,
        refs.segment_tokenization_review_ref(DOC, SEGMENT).kind,
        refs.segment_glosses_ref(DOC, SEGMENT).kind,
        refs.segment_gloss_review_ref(DOC, SEGMENT).kind,
        refs.segment_grammar_notes_ref(DOC, SEGMENT).kind,
        refs.segment_grammar_review_ref(DOC, SEGMENT).kind,
        refs.segment_context_notes_ref(DOC, SEGMENT).kind,
        refs.segment_context_review_ref(DOC, SEGMENT).kind,
        refs.entity_index_ref(DOC).kind,
        refs.term_index_ref(DOC).kind,
        refs.glossary_draft_ref(DOC).kind,
        refs.paragraph_assembly_package_ref(DOC, PARAGRAPH).kind,
        refs.paragraph_assembly_validation_ref(DOC, PARAGRAPH).kind,
        refs.paragraph_assembly_review_ref(DOC, PARAGRAPH).kind,
        refs.package_validation_ref(DOC).kind,
    }
    assert produced == set(ArtifactKind)


def test_document_scope_rejects_chapter_id() -> None:
    with pytest.raises(ValueError, match="does not accept chapter_id"):
        _make_ref(
            ArtifactKind.CHAPTER_PROPOSAL,
            document_id=DOC,
            chapter_id=CHAPTER,
        )


def test_segment_scope_requires_segment_id() -> None:
    with pytest.raises(ValueError, match="requires segment_id"):
        _make_ref(ArtifactKind.TOKENIZATION, document_id=DOC)


def test_paragraph_assembly_package_path() -> None:
    ref = refs.paragraph_assembly_package_ref(DOC, PARAGRAPH)
    path = artifact_path(Path("/repo"), ref)
    assert str(path).endswith(f"jobs/assembly/{PARAGRAPH}/package.json")
