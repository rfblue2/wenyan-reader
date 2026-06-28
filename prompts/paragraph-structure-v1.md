## Task

Identify paragraph boundaries within the chapter text below. Each paragraph is a contiguous span with character offsets relative to the chapter text (0-based start, end exclusive). Paragraphs must partition the full chapter text without gaps or overlaps.

promptVersion: paragraph-structure-v1

Chapter text:
{{chapter_text}}

DOCUMENT_ID: {{document_id}}
CHAPTER_ID: {{chapter_id}}
INPUT_HASH: {{input_hash}}
CHAPTER_TEXT_HASH: {{chapter_text_hash}}
