## Task

Draft grammar notes for the reviewed tokenization below.

## Grammar rules

- Explain **salient Classical Chinese constructions** in this segment only.
- Anchor each note to one or more `anchorTokenIds` from the tokenization.
- Write for an English-speaking learner. Avoid generic textbook filler.
- Return `grammarNotes: []` when the segment has no construction worth calling out.
- Use `type` `grammar` on every note.
- Generate a new UUID v4 for each note `id`.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- List drafted notes in `grammarNotes`.

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Local context:
{{local_context_json}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
