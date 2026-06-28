## Task

Split the paragraph text below into reader segments—contiguous units sized for reading and glossing.

## Segmentation rules

- **Default: one sentence per segment.** Sentences usually end at `。`, `！`, `？`, or `；`. Do not split on commas alone within a single sentence.
- **Combine short sentences** when several consecutive sentences are very short and read better together (for example, a run of brief parallel clauses or a short list). The whole passage may be one segment, or split roughly in half—use judgment.
- **Split very long sentences** only when a single sentence exceeds about 48 characters. Use natural clause boundaries (commas, parallel phrases) and your judgment; each resulting segment should still be a coherent reading unit.
- Keep speaker attributions with what they introduce (for example, `孫子曰：` belongs with the following sentence, not as its own segment).

## Examples (follow the rules, not these exact splits)

1. `孫子曰：兵者，國之大事，死生之地，存亡之道，不可不察也。` → one segment.
2. A paragraph of three sentences such as `兵者，詭道也。…此兵家之勝，不可先傳也。` → one segment per sentence (three segments).
3. `故校之以計，而索其情，曰：主孰有道？將孰有能？…` with many short clauses → one segment for the whole passage, or two segments—either is acceptable.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `paragraphId` and `inputHash` from PARAGRAPH_ID and INPUT_HASH below.
- Each segment needs a new UUID v4 `id` and `text` that is an exact substring of the paragraph text.
- Concatenating segment texts in order must reproduce the full paragraph text.
- Include `draftRationale.segmentation` with a brief note on the splits; use an empty `paragraphContextNotes` array unless cross-segment context is genuinely needed.

Paragraph text:
{{paragraph_text}}

PARAGRAPH_ID: {{paragraph_id}}
INPUT_HASH: {{input_hash}}
