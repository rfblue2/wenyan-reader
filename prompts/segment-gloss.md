## Task

Select or propose glosses for each token in the reviewed tokenization below.

## Gloss rules

- Provide **one `glossDecisions` entry per token** in the tokenization. Do not merge, split, or skip tokens.
- Gloss the **local sense of each token surface** as tokenized. If tokenization used single characters (`國`, `之`, `不`), gloss each character separately; do not gloss a multi-word phrase unless that exact surface appears as one token.
- **Reuse before creating.** The candidate glosses list contains only entries whose surface appears among this segment's token surfaces (not the entire document glossary). When a token's local sense matches an existing entry (same surface, pinyin, and gloss sense), you **must** use `reuse-existing` with that entry's `glossId`. Do not mint a new id for the same sense.
- Create `create-new` only for senses not already in candidate glosses. Distinct senses of the same character still get separate gloss entries.
- **Pinyin must match local sense**, especially for polyphonic characters. Use tone-marked Hanyu Pinyin (`jiàng`, not `jiang`).
  - In `四曰將` (commander as one of the five factors), `將` → **`jiàng`**, gloss “general; commander”.
  - In `將聽吾計` (if/when [the ruler] will hear my plan), `將` → **`jiāng`**, gloss the future auxiliary, not “general”.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- Use `decision` `reuse-existing` when a candidate gloss matches the local sense; otherwise use `create-new`.
- When reusing, set `glossId` to the existing candidate gloss id and leave `newGlosses` / `newGlossIds` empty for that token.
- When creating, add the new gloss to `newGlosses` with a new UUID v4 `id`, accurate `pinyin`, and a concise English `gloss`.
- List every newly introduced gloss id in `newGlossIds`.

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Candidate glosses:
{{candidate_glosses_json}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
