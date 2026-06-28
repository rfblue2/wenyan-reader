## Task

Review the gloss decisions below for a Classical Chinese reader.

## Review checklist

- Reject for gloss quality: **wrong sense in context**, **wrong pinyin** (including tone), duplicate new glosses, missing token coverage, or gloss/token mismatch.
- Every token in the tokenization must have exactly one `glossDecisions` entry; reject if any token is missing or duplicated.
- Gloss entries must match **token surfaces** as tokenized (single-character tokens get single-character glosses).
- **Polyphonic characters:** pinyin must match the sense used in this segment, not a default dictionary reading. Reject when sense and pinyin disagree.
  - Example: in `四曰將` (the fourth of the five factors is the commander), `將` means general/commander and should be **`jiàng`**, not `jiāng` (the auxiliary “will/shall”).
  - Example: in `將聽吾計`, `將` is the future auxiliary and should be **`jiāng`**, not `jiàng`.
- Reject when a `create-new` decision duplicates an existing candidate gloss (same surface, pinyin, and sense) instead of reusing its `glossId`.
- Use the **segment text** below to judge context; do not approve a gloss whose English sense or pinyin fits a different reading of the same character elsewhere.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` from SEGMENT_ID below.
- Set `inputHash` from REVIEW_INPUT_HASH below. This hashes the gloss artifact you are reviewing.
- Set `status` to `approved` only when gloss sense, **context-appropriate pinyin**, and homonym handling are all correct; otherwise set `status` to `rejected`.
- When rejecting, include one or more objects in `findings` describing each problem (`tokenId`, `surface`, `problem`, `detail`); use an empty `findings` array when approved.
- Never reject because review and gloss `inputHash` values differ from upstream artifacts.

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Glosses:
{{glosses_json}}

Candidate glosses (document glossary so far — reuse these ids when matched):
{{candidate_glosses_json}}

SEGMENT_ID: {{segment_id}}
REVIEW_INPUT_HASH: {{review_input_hash}}
