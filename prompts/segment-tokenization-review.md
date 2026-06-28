## Task

Review the tokenization artifact below for a Classical Chinese reader.

## Review checklist

- Reject if any token is punctuation or whitespace only.
- Reject if tokens are **too coarse**: long phrases that should be split into single characters and small compounds, especially across `之` or other particles (for example reject `國之大事` when it should be `國` / `之` / `大事`).
- Reject if tokens are **too fine**: names, idioms, or fixed compounds incorrectly split (for example `孫子` or `大事` split into single characters).
- **Prefer single-character tokens** for ordinary words and particles; allow multi-character tokens only for names, titles, places, and fixed compounds that read as one gloss unit.
- For `孫子曰：兵者，國之大事，死生之地，存亡之道，不可不察也。`, acceptable token surfaces are: `孫子`, `曰`, `兵者`, `國`, `之`, `大事`, `死生`, `之`, `地`, `存亡`, `之`, `道`, `不`, `可`, `不`, `察`, `也` (punctuation not tokenized).
- Reject for overlaps, wrong surfaces, bad offsets, or missing glossable characters.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` from SEGMENT_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the tokenization artifact you are reviewing. Do not compare it to `inputHash` inside the tokenization JSON — that field hashes the original segment text and is expected to differ.
- Set `status` to `approved` when tokens correctly identify glossable units with valid offsets; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings` describing each problem; use an empty `findings` array when approved.
- Never reject because review and tokenization `inputHash` values differ.

Tokenization:
{{tokenization_json}}

SEGMENT_ID: {{segment_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
