## Task

Review the segment-local context notes below for a Classical Chinese reader.

## Review checklist

- Context notes must be useful and anchored correctly.
- Factual or interpretive claims must be **source-grounded** when source snippets were available.
- Reject unsupported historical, literary, or biographical claims.
- Reject notes that duplicate paragraph-level context notes when those are provided.
- When glosses are provided, reject notes that conflict with selected gloss senses.
- Approve `contextNotes: []` when no segment-local context was needed.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` from SEGMENT_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the context artifact you are reviewing.
- Set `status` to `approved` only when context notes pass the checklist; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings`; use an empty `findings` array when approved.
- Populate `sourceGrounding` for context notes that make factual claims.

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Context notes:
{{context_notes_json}}

Glosses (optional — null when not yet drafted):
{{glosses_json}}

Local context:
{{local_context_json}}

Source snippets:
{{source_snippets_json}}

Paragraph-level context notes:
{{paragraph_context_notes_json}}

SEGMENT_ID: {{segment_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
