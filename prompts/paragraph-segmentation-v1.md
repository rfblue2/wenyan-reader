## Task

Split the paragraph text below into reader segments—contiguous units short enough for tokenization and reading.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `paragraphId` and `inputHash` from PARAGRAPH_ID and INPUT_HASH below.
- Set `promptVersion` to `paragraph-segmentation-v1`.
- Each segment needs a new UUID v4 `id` and `text` that is an exact substring of the paragraph text.
- Concatenating segment texts in order must reproduce the full paragraph text.
- Include `draftRationale.segmentation` with a brief note on the splits; use an empty `paragraphContextNotes` array unless cross-segment context is genuinely needed.

promptVersion: paragraph-segmentation-v1

Paragraph text:
{{paragraph_text}}

PARAGRAPH_ID: {{paragraph_id}}
INPUT_HASH: {{input_hash}}
