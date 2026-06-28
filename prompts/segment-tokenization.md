## Task

Tokenize the segment text below for a Classical Chinese reader.

## Tokenization rules

- Tokens identify **glossable** text only. Do not create tokens for punctuation or whitespace.
- Punctuation (for example `，。、；：？！` and quotation marks) stays in `text` and appears between tokens in the reader; it is never glossed.
- Tokens must be ordered, non-overlapping, and each `surface` must equal `text[start:end]`.
- Offsets are 0-based character positions relative to the segment text; `end` is exclusive.

### Prefer single characters

- **Default to one character per token** for ordinary words and grammatical particles (`之`, `也`, `而`, `以`, `於`, `其`, `不`, `可`, and similar).
- Use **multi-character tokens sparingly**, only when the reader should gloss the span as one unit:
  - Personal names and titles (`孫子`)
  - Place names
  - Fixed binomes or compounds whose sense is not the sum of parts (`大事`, `死生`, `存亡`)
  - Established idioms or set phrases in context (`兵者` when it functions as a topic label)
- **Do not merge across grammar particles.** Split `國/之/大事`, not `國之大事`. Split `死生/之/地`, not `死生之地`.
- **Do not produce long phrase tokens** that span multiple clauses or several content words joined only by `之` or punctuation.

### Example

For `孫子曰：兵者，國之大事，死生之地，存亡之道，不可不察也。` (punctuation omitted from tokens):

`孫子` / `曰` / `兵者` / `國` / `之` / `大事` / `死生` / `之` / `地` / `存亡` / `之` / `道` / `不` / `可` / `不` / `察` / `也`

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- Set `text` to the segment text exactly as given below.
- Each token needs a unique string `id`, `surface`, `start`, and `end`.

Segment text:
{{segment_text}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
