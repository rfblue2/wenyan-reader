from __future__ import annotations

import json

from wenyan_models.artifacts.paragraph import ParagraphDraft

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.assembly.load_segment_outputs import CompiledSegmentInputs


def segment_output_hash(outputs: CompiledSegmentInputs) -> str:
    parts = (
        outputs.tokenization.model_dump_json(by_alias=True),
        outputs.glosses.model_dump_json(by_alias=True),
        outputs.grammar_notes.model_dump_json(by_alias=True),
        outputs.context_notes.model_dump_json(by_alias=True),
    )
    return str(sha256_text("".join(parts)))


def assembly_input_hash(
    draft: ParagraphDraft,
    segment_hashes: dict[str, str],
) -> str:
    payload = {
        "draft": draft.model_dump(by_alias=True, mode="json"),
        "segments": segment_hashes,
    }
    return str(sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False)))
