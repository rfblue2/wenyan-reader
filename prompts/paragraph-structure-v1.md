## Task

Identify paragraph boundaries within the chapter text below.

## Output

Return one JSON object only, matching the schema from the system instructions.

- Set `documentId`, `chapterId`, `inputHash`, and `chapterTextHash` from the labeled fields below.
- Set `promptVersion` to `paragraph-structure-v1`.
- Each paragraph needs a new UUID v4 `id`, `start`, `end`, and `rationale`.
- Offsets are 0-based character positions relative to the chapter text; `end` is exclusive.
- Paragraphs must partition the full chapter text from offset 0 through len(chapter text) with no gaps or overlaps.

promptVersion: paragraph-structure-v1

Chapter text:
{{chapter_text}}

DOCUMENT_ID: {{document_id}}
CHAPTER_ID: {{chapter_id}}
INPUT_HASH: {{input_hash}}
CHAPTER_TEXT_HASH: {{chapter_text_hash}}
