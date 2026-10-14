# Reader Package

> **Spec** — the files the reader app consumes. Written only by `package-document`. Pydantic models: `packages/wenyan-models/src/wenyan_models/reader/`. Planned changes live in the [backlog](../backlog.md).

The reader loads validated local files from `content/documents/<document-id>/`, committed to git. It never reads preprocessing artifacts and never calls an LLM. Content is split per paragraph so large documents load incrementally.

## Layout

```text
content/documents/<document-id>/
  document.json
  glosses/index.json
  chapters/<chapter-id>/
    chapter.json
    paragraphs/<paragraph-id>.json
```

All ids are UUIDs. A package may be partial: it contains only paragraphs whose assembly passed, and only chapters with at least one such paragraph.

## `document.json`

Entry point.

```json
{
  "schemaVersion": 1,
  "id": "12ea50f2-…",
  "title": "孙子兵法",
  "glossIndexPath": "glosses/index.json",
  "chapters": [
    {"id": "481af6b4-…", "title": "始計第一", "path": "chapters/481af6b4-…/chapter.json"}
  ]
}
```

## `chapter.json`

Navigation only.

```json
{
  "id": "481af6b4-…",
  "title": "始計第一",
  "paragraphs": [{"id": "048109b3-…", "path": "paragraphs/048109b3-….json"}]
}
```

## Paragraph file

The reading content: ordered segments with tokens and notes.

```json
{
  "id": "c777d984-…",
  "segments": [
    {
      "id": "d70e05cc-…",
      "text": "孟子見梁惠王。",
      "newGlossIds": ["7d0d9c78-…"],
      "tokens": [
        {"id": "3723a8d9-…", "surface": "孟子", "start": 0, "end": 2, "glossId": "7d0d9c78-…"}
      ],
      "notes": []
    }
  ]
}
```

- `text` is the display string, punctuation included.
- `tokens` are the clickable spans; `start`/`end` index into `text`. Punctuation is not tokenized.
- `glossId` picks the sense for this occurrence. The same surface can map to different glosses.
- `newGlossIds` lists glosses this segment introduces (content-defined, not per-user).
- `notes` defaults to `[]`.

## `glosses/index.json`

Document glossary. One entry per sense; a surface may have several.

```json
{
  "glosses": [
    {"id": "5f04fd59-…", "surface": "之", "pinyin": "zhī", "gloss": "possessive or attributive particle; of"},
    {"id": "4b787781-…", "surface": "之", "pinyin": "zhī", "gloss": "third-person object pronoun; him, her, it, them"}
  ]
}
```

Copied from the preprocessing glossary draft, so it may include entries no packaged token uses.

## Notes

Notes live in the segment they annotate.

```json
{
  "id": "6f79c527-…",
  "type": "context",
  "anchorTokenIds": ["3723a8d9-…"],
  "body": "Mencius is being introduced in an audience with a ruler.",
  "sources": [{"label": "Mencius 1A1", "detail": "Supporting excerpt."}]
}
```

- `type` is `grammar` or `context`. Grammar notes have no `sources`.
- `sources[].detail` is the citation excerpt. Citation `url` and `accessedAt` are dropped at assembly.
- Paragraph-level context notes are attached to the earliest token of their first anchored segment.

## Validation

`assemble-paragraph` and `package-document` check:

| Check | Where |
|---|---|
| Segment order matches the paragraph draft; segment texts concatenate to the draft | assembly |
| Token ids unique within a segment | assembly |
| Every token has a gloss decision | assembly |
| Note anchors reference tokens in the same segment | assembly, package |
| Every `glossId` and `newGlossIds` entry exists in the gloss index | package |
| Chapter and paragraph ids unique; paths well-formed; chapters/paragraphs reachable from the manifest | package (in memory, not on disk) |

Not checked: token offsets against `text`, segment/note/gloss id uniqueness across the document, existence of referenced files on disk.
