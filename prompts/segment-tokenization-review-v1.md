## Task

Review the tokenization artifact below for a Classical Chinese reader.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- Set `promptVersion` to `segment-tokenization-review-v1`.
- Set `status` to `approved` when tokens correctly partition the segment text; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings` describing each problem; use an empty `findings` array when approved.

promptVersion: segment-tokenization-review-v1

Tokenization:
{{tokenization_json}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
