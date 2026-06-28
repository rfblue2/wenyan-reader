## Task

Review the tokenization artifact below for a Classical Chinese reader.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` from SEGMENT_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the tokenization artifact you are reviewing. Do not compare it to `inputHash` inside the tokenization JSON — that field hashes the original segment text and is expected to differ.
- Set `promptVersion` to `segment-tokenization-review-v1`.
- Set `status` to `approved` when tokens correctly partition the segment text; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings` describing each problem; use an empty `findings` array when approved.
- Reject only for tokenization quality (gaps, overlaps, wrong surfaces, bad offsets). Never reject because review and tokenization `inputHash` values differ.

promptVersion: segment-tokenization-review-v1

Tokenization:
{{tokenization_json}}

SEGMENT_ID: {{segment_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
