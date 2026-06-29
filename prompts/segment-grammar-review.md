## Task

Review the grammar notes below for a Classical Chinese reader.

## Review checklist

- Grammar notes must describe constructions **actually present** in the segment.
- Anchors must point to the correct token IDs.
- Notes should be useful for comprehension, not generic filler.
- When glosses are provided, reject notes that **conflict with selected gloss senses**.
- Reject notes with empty bodies, missing anchors, or anchors outside the tokenization.
- Approve `grammarNotes: []` when no salient construction was worth annotating.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` from SEGMENT_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the grammar artifact you are reviewing.
- Set `status` to `approved` only when grammar notes pass the checklist; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings`; use an empty `findings` array when approved.

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Grammar notes:
{{grammar_notes_json}}

Glosses (optional — null when not yet drafted):
{{glosses_json}}

Local context:
{{local_context_json}}

SEGMENT_ID: {{segment_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
