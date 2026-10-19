import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import (
    ParagraphArtifactKind,
    ParagraphRef,
    SegmentArtifactKind,
    SegmentRef,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.segment_pipeline import segment_is_complete
from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import ContentHash, DocumentId, ParagraphId, SegmentId


@dataclass(frozen=True)
class SegmentOutputs:
    segment_id: SegmentId
    tokenization: TokenizationArtifact
    glosses: GlossesArtifact
    grammar_notes: GrammarNotesArtifact
    context_notes: ContextNotesArtifact


class AssemblyState(StrEnum):
    UNASSEMBLED = "unassembled"
    STALE = "stale"
    FAILED = "failed"
    CURRENT = "current"


@dataclass(frozen=True)
class ParagraphAssembly:
    """A paragraph whose segments are all complete; `segments` is in draft order."""

    draft: ParagraphDraft
    segments: tuple[SegmentOutputs, ...]
    input_hash: ContentHash
    state: AssemblyState


@dataclass(frozen=True)
class SegmentsIncomplete:
    segment_id: SegmentId


def inspect_paragraph_assembly(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> ParagraphAssembly | SegmentsIncomplete | None:
    """None when the paragraph has no draft."""
    draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph_id)
    if not artifacts.exists(draft_ref):
        return None
    draft = artifacts.read(draft_ref, ParagraphDraft)
    for segment in draft.segments:
        if not segment_is_complete(artifacts, document_id, segment.id):
            return SegmentsIncomplete(segment.id)
    segments = tuple(
        _load_segment_outputs(artifacts, document_id, segment.id) for segment in draft.segments
    )
    input_hash = assembly_input_hash(draft, segments)
    return ParagraphAssembly(
        draft=draft,
        segments=segments,
        input_hash=input_hash,
        state=_assembly_state(artifacts, document_id, paragraph_id, input_hash),
    )


def assembly_input_hash(draft: ParagraphDraft, segments: Sequence[SegmentOutputs]) -> ContentHash:
    payload = {
        "draft": draft.model_dump(by_alias=True, mode="json"),
        "segments": {segment.segment_id: _segment_output_hash(segment) for segment in segments},
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def _segment_output_hash(segment: SegmentOutputs) -> ContentHash:
    return sha256_text(
        segment.tokenization.model_dump_json(by_alias=True)
        + segment.glosses.model_dump_json(by_alias=True)
        + segment.grammar_notes.model_dump_json(by_alias=True)
        + segment.context_notes.model_dump_json(by_alias=True),
    )


def _load_segment_outputs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> SegmentOutputs:
    def ref(kind: SegmentArtifactKind) -> SegmentRef:
        return SegmentRef(kind, document_id, segment_id)

    return SegmentOutputs(
        segment_id=segment_id,
        tokenization=artifacts.read(ref(SegmentArtifactKind.TOKENIZATION), TokenizationArtifact),
        glosses=artifacts.read(ref(SegmentArtifactKind.GLOSSES), GlossesArtifact),
        grammar_notes=artifacts.read(ref(SegmentArtifactKind.GRAMMAR_NOTES), GrammarNotesArtifact),
        context_notes=artifacts.read(ref(SegmentArtifactKind.CONTEXT_NOTES), ContextNotesArtifact),
    )


def _assembly_state(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
    input_hash: ContentHash,
) -> AssemblyState:
    validation_ref = ParagraphRef(ParagraphArtifactKind.ASSEMBLY_VALIDATION, document_id, paragraph_id)
    if not artifacts.exists(validation_ref):
        return AssemblyState.UNASSEMBLED
    validation = artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
    if validation.input_hash != input_hash:
        return AssemblyState.STALE
    if validation.status == ValidationStatus.FAILED:
        return AssemblyState.FAILED
    package_ref = ParagraphRef(ParagraphArtifactKind.ASSEMBLY_PACKAGE, document_id, paragraph_id)
    if not artifacts.exists(package_ref):
        return AssemblyState.UNASSEMBLED
    return AssemblyState.CURRENT
