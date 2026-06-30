from dataclasses import dataclass

from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import SegmentId


@dataclass(frozen=True)
class CompiledSegmentInputs:
    segment_id: SegmentId
    text: str
    tokenization: TokenizationArtifact
    glosses: GlossesArtifact
    grammar_notes: GrammarNotesArtifact
    context_notes: ContextNotesArtifact
