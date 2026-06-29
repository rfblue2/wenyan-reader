# Storage Format

## Purpose

Define the local content representation for curated Classical Chinese documents.

The first-stage app should use local files as the source of truth. The format must support full documents with chapters, paragraphs, and many bite-sized reading segments without requiring a single huge JSON file.

Preprocessing writes validated package files under `content/documents/<document-id>/`. Intermediate preprocessing artifacts live separately under `preprocess/documents/<document-id>/`. See [Intermediate Artifacts](preprocessing/intermediate-artifacts.md).

## Design Goals

- Keep content reviewable in version control.
- Allow large documents to be loaded incrementally.
- Keep only fields needed by the app.
- Support document-level glossary aggregation.
- Support precise token-level gloss disambiguation.
- Preserve room for source-grounded editorial review.

## Directory Shape

```text
content/
  documents/
    document-id/
      document.json
      glosses/
        index.json
      chapters/
        chapter-id/
          chapter.json
          paragraphs/
            paragraph-id.json
```

Persisted IDs should be UUIDs. Human-readable IDs may be useful in examples, but UUIDs are safer once content is generated, split, revised, and merged.

## Document Manifest

`document.json` is the entry point for a document.

```json
{
  "schemaVersion": 1,
  "id": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
  "title": "三國志",
  "glossIndexPath": "glosses/index.json",
  "chapters": [
    {
      "id": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
      "title": "卷一",
      "path": "chapters/6c708ee9-95c0-4d23-8a4f-8cb5fd62c605/chapter.json"
    }
  ]
}
```

Required fields:

- `schemaVersion`
- `id`
- `title`
- `glossIndexPath`
- `chapters`

## Chapter File

`chapter.json` contains chapter-level navigation only.

```json
{
  "id": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
  "title": "卷一",
  "paragraphs": [
    {
      "id": "c777d984-afd6-4a31-aa34-2d26d29fb445",
      "path": "paragraphs/c777d984-afd6-4a31-aa34-2d26d29fb445.json"
    }
  ]
}
```

Required fields:

- `id`
- `title`
- `paragraphs`

## Paragraph File

Paragraph files contain the actual reading content. A paragraph may contain one or more text segments.

```json
{
  "id": "c777d984-afd6-4a31-aa34-2d26d29fb445",
  "segments": [
    {
      "id": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
      "text": "孟子見梁惠王。",
      "newGlossIds": ["7d0d9c78-8307-4f11-9352-63b5d74af0fd"],
      "tokens": [
        {
          "id": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
          "surface": "孟子",
          "start": 0,
          "end": 2,
          "glossId": "7d0d9c78-8307-4f11-9352-63b5d74af0fd"
        }
      ],
      "notes": []
    }
  ]
}
```

Required fields:

- `id`
- `segments`
- Segment `id`, `text`, `newGlossIds`, `tokens`, and `notes`
- Token `id`, `surface`, `start`, `end`, and `glossId`

`newGlossIds` is content-defined. It lists glosses pedagogically introduced by that segment and does not depend on saved user history.

## Gloss Index

`glosses/index.json` is the document-level glossary.

```json
{
  "glosses": [
    {
      "id": "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
      "surface": "孟子",
      "pinyin": "Mengzi",
      "gloss": "Mencius"
    },
    {
      "id": "5f04fd59-e3bb-4f8e-8e15-a37f94d9eec7",
      "surface": "之",
      "pinyin": "zhi",
      "gloss": "possessive or attributive particle; of"
    },
    {
      "id": "4b787781-8f90-46bc-9455-f106134580a4",
      "surface": "之",
      "pinyin": "zhi",
      "gloss": "third-person object pronoun; him, her, it, them"
    }
  ]
}
```

Required fields:

- `id`
- `surface`
- `pinyin`
- `gloss`

The same surface form may appear in multiple gloss entries. Token occurrences choose the correct `glossId` for their local context.

## Notes

Notes live inside the segment they annotate.

```json
{
  "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
  "type": "context",
  "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
  "body": "Mencius is being introduced in an audience with a ruler.",
  "sources": [
    {
      "label": "Mencius 1A1",
      "detail": "Used to verify the immediate passage context."
    }
  ]
}
```

Required fields:

- `id`
- `type`
- `anchorTokenIds`
- `body`

Optional fields:

- `sources`

`sources` may be ignored by the reader UI in stage one, but preprocessing and editorial review should preserve it.

## Validation Requirements

The app and preprocessing tools should validate:

- All referenced paths exist.
- All IDs are unique within their scope.
- Token offsets reconstruct the segment text.
- Every token points to an existing gloss.
- Every note anchors to tokens in the same segment.
- All chapters, paragraphs, and segments are reachable from `document.json`.
