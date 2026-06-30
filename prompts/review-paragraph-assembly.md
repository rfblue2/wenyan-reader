## Task

Review the assembled paragraph package below for a Classical Chinese reader.

## Review checklist

- The assembled paragraph still reads as the original paragraph when segment texts are read in order.
- Segment outputs are internally consistent when read together (tokens, glosses, and notes align across segment boundaries).
- Paragraph-level context notes do not duplicate or conflict with segment-local grammar or context notes.
- New gloss introductions are pedagogically sensible in paragraph context (sense and pinyin fit the passage).

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `paragraphId` from PARAGRAPH_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the assembled paragraph package you are reviewing.
- Set `status` to `approved` only when the checklist passes; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings` describing each problem; use an empty `findings` array when approved.
- Never reject because review and package `inputHash` values differ from upstream artifacts.

Paragraph draft (structure and paragraph-level context notes):
{{paragraph_draft_json}}

Assembled paragraph package:
{{paragraph_package_json}}

PARAGRAPH_ID: {{paragraph_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
