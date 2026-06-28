## Task

Tokenize the segment text below for a Classical Chinese reader.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- Set `promptVersion` to `segment-tokenization-v1`.
- Set `text` to the segment text exactly as given below.
- Each token needs a unique string `id`, `surface`, `start`, and `end`.
- Offsets are 0-based character positions relative to the segment text; `end` is exclusive.
- Tokens must partition the full segment text with no gaps or overlaps.

promptVersion: segment-tokenization-v1

Segment text:
{{segment_text}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
