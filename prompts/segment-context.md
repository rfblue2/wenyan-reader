## Task

Draft segment-local context notes for the reviewed tokenization below.

## Context rules

- Explain people, places, historical setting, literary references, or interpretive context needed to understand the segment.
- Anchor each note to relevant `anchorTokenIds` from the tokenization.
- Cite `sourceId` from provided source snippets when making factual or interpretive claims.
- Return `contextNotes: []` when no context beyond the segment text itself is needed.
- Use `type` `context` on every note.
- Generate a new UUID v4 for each note `id`.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- List drafted notes in `contextNotes`.

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Local context:
{{local_context_json}}

Source snippets:
{{source_snippets_json}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
