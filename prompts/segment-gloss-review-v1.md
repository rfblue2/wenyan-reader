## Task

Review the gloss decisions below for a Classical Chinese reader.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` from SEGMENT_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the gloss artifact you are reviewing.
- Set `promptVersion` to `segment-gloss-review-v1`.
- Set `status` to `approved` when gloss sense selection, pinyin, and homonym handling are correct; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings` describing each problem; use an empty `findings` array when approved.
- Reject for gloss quality only: wrong sense, bad pinyin, duplicate new glosses, missing token coverage, or gloss/token mismatch.

promptVersion: segment-gloss-review-v1

Glosses:
{{glosses_json}}

SEGMENT_ID: {{segment_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
