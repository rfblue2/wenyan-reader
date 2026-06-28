## Task

Select or propose glosses for each token in the reviewed tokenization below.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `segmentId` and `inputHash` from SEGMENT_ID and INPUT_HASH below.
- Set `promptVersion` to `segment-gloss-v1`.
- Provide one `glossDecisions` entry for every token in the tokenization.
- Use `decision` `reuse-existing` when a candidate gloss matches the local sense; otherwise use `create-new`.
- When reusing, set `glossId` to the existing candidate gloss id.
- When creating, add the new gloss to `newGlosses` with a new UUID v4 `id`, accurate `pinyin`, and a concise English `gloss`.
- List every newly introduced gloss id in `newGlossIds`.
- Prefer reusing candidate glosses when the sense matches; create separate gloss entries for distinct senses of the same surface form.

promptVersion: segment-gloss-v1

Segment text:
{{segment_text}}

Tokenization:
{{tokenization_json}}

Candidate glosses:
{{candidate_glosses_json}}

SEGMENT_ID: {{segment_id}}
INPUT_HASH: {{input_hash}}
