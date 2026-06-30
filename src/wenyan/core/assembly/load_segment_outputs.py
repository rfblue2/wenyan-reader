from dataclasses import dataclass

from wenyan.core.ports.artifact_ref import (
    segment_context_notes_ref,
    segment_glosses_ref,
    segment_grammar_notes_ref,
    segment_tokenization_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import DocumentId, SegmentId


@dataclass(frozen=True)
class CompiledSegmentInputs:
    segment_id: SegmentId
    text: str
    tokenization: TokenizationArtifact
    glosses: GlossesArtifact
    grammar_notes: GrammarNotesArtifact
    context_notes: ContextNotesArtifact


class MissingSegmentOutputError(ValueError):
    pass


def load_segment_outputs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> CompiledSegmentInputs:
    tokenization_ref = segment_tokenization_ref(document_id, segment_id)
    glosses_ref = segment_glosses_ref(document_id, segment_id)
    grammar_notes_ref = segment_grammar_notes_ref(document_id, segment_id)
    context_notes_ref = segment_context_notes_ref(document_id, segment_id)
    for ref, label in (
        (tokenization_ref, "tokenization"),
        (glosses_ref, "glosses"),
        (grammar_notes_ref, "grammar-notes"),
        (context_notes_ref, "context-notes"),
    ):
        if not artifacts.exists(ref):
            raise MissingSegmentOutputError(f"{label} artifact is missing for segment {segment_id}")
    tokenization = artifacts.read(tokenization_ref, TokenizationArtifact)
    glosses = artifacts.read(glosses_ref, GlossesArtifact)
    grammar_notes = artifacts.read(grammar_notes_ref, GrammarNotesArtifact)
    context_notes = artifacts.read(context_notes_ref, ContextNotesArtifact)
    return CompiledSegmentInputs(
        segment_id=segment_id,
        text=tokenization.text,
        tokenization=tokenization,
        glosses=glosses,
        grammar_notes=grammar_notes,
        context_notes=context_notes,
    )


def load_all_segment_outputs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    draft: ParagraphDraft,
) -> tuple[CompiledSegmentInputs, ...]:
    return tuple(
        load_segment_outputs(artifacts, document_id, segment.id) for segment in draft.segments
    )
