from wenyan.core.ports.artifact_ref import (
    ChapterArtifactKind,
    ChapterRef,
    DocumentArtifactKind,
    DocumentRef,
    ParagraphArtifactKind,
    ParagraphRef,
    SegmentArtifactKind,
    SegmentRef,
)
from wenyan_models.domain.ids import chapter_id, document_id, paragraph_id, segment_id

DOC = document_id("doc")

# Paths relative to preprocess/documents/doc/.
DOCUMENT_LAYOUT = {
    DocumentArtifactKind.NORMALIZED_DOCUMENT: "normalized-document.json",
    DocumentArtifactKind.CHAPTER_PROPOSAL: "structure/chapter-proposal.json",
    DocumentArtifactKind.CHAPTER_PROPOSAL_VALIDATION: "structure/chapter-proposal.validation.json",
    DocumentArtifactKind.GLOSSARY_DRAFT: "indexes/glossary-draft.json",
    DocumentArtifactKind.PACKAGE_VALIDATION: "jobs/package/validation.json",
}
CHAPTER_LAYOUT = {
    ChapterArtifactKind.PARAGRAPH_PROPOSAL: "structure/chapters/ch/paragraph-proposal.json",
    ChapterArtifactKind.PARAGRAPH_PROPOSAL_VALIDATION: (
        "structure/chapters/ch/paragraph-proposal.validation.json"
    ),
}
PARAGRAPH_LAYOUT = {
    ParagraphArtifactKind.DRAFT: "jobs/paragraphs/para/draft.json",
    ParagraphArtifactKind.DRAFT_VALIDATION: "jobs/paragraphs/para/validation.json",
    ParagraphArtifactKind.ASSEMBLY_PACKAGE: "jobs/assembly/para/package.json",
    ParagraphArtifactKind.ASSEMBLY_VALIDATION: "jobs/assembly/para/validation.json",
}
SEGMENT_LAYOUT = {
    SegmentArtifactKind.INPUT: "jobs/segments/seg/input.json",
    SegmentArtifactKind.TOKENIZATION: "jobs/segments/seg/tokenization.json",
    SegmentArtifactKind.TOKENIZATION_REVIEW: "jobs/segments/seg/tokenization-review.json",
    SegmentArtifactKind.GLOSSES: "jobs/segments/seg/glosses.json",
    SegmentArtifactKind.GLOSS_REVIEW: "jobs/segments/seg/gloss-review.json",
    SegmentArtifactKind.GRAMMAR_NOTES: "jobs/segments/seg/grammar-notes.json",
    SegmentArtifactKind.GRAMMAR_REVIEW: "jobs/segments/seg/grammar-review.json",
    SegmentArtifactKind.CONTEXT_NOTES: "jobs/segments/seg/context-notes.json",
    SegmentArtifactKind.CONTEXT_REVIEW: "jobs/segments/seg/context-review.json",
}


def test_relative_path_pins_on_disk_layout() -> None:
    assert set(DOCUMENT_LAYOUT) == set(DocumentArtifactKind)
    assert set(CHAPTER_LAYOUT) == set(ChapterArtifactKind)
    assert set(PARAGRAPH_LAYOUT) == set(ParagraphArtifactKind)
    assert set(SEGMENT_LAYOUT) == set(SegmentArtifactKind)
    cases = [
        *((DocumentRef(kind, DOC), path) for kind, path in DOCUMENT_LAYOUT.items()),
        *((ChapterRef(kind, DOC, chapter_id("ch")), path) for kind, path in CHAPTER_LAYOUT.items()),
        *(
            (ParagraphRef(kind, DOC, paragraph_id("para")), path)
            for kind, path in PARAGRAPH_LAYOUT.items()
        ),
        *(
            (SegmentRef(kind, DOC, segment_id("seg")), path)
            for kind, path in SEGMENT_LAYOUT.items()
        ),
    ]
    for ref, path in cases:
        assert ref.relative_path.as_posix() == f"preprocess/documents/doc/{path}"
