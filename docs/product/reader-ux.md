# Reader UX

> **Product** — intended student-facing reading experience. **Not built yet**; see the [backlog](../backlog.md). Data comes from the [Reader Package](../spec/reader-package.md).

Prioritize uninterrupted reading. Glosses and notes support comprehension but never dominate the page.

## Core Principles

- Show one segment at a time.
- Keep the main reading surface visually quiet.
- Let the reader request help only when needed.
- Preserve access to all glosses and notes wherever they appear.
- Avoid turning the reader into an interlinear translation or study worksheet.

## Primary Views

### Library View

Lists available documents by title.

### Reader View

Shows the current segment and reading controls:

- Current segment text.
- Previous and next navigation.
- Optional access to chapter or paragraph navigation.
- Controls for revealing new glosses or notes.

Default quiet reading layout:

```text
+------------------------------------------------------+
| 三國志                                      卷一      |
+------------------------------------------------------+
|                                                      |
|                                                      |
|          孟子見梁惠王。                              |
|                                                      |
|          王曰：叟，不遠千里而來，                    |
|          亦將有以利吾國乎？                          |
|                                                      |
|                                                      |
+------------------------------------------------------+
|  < Previous        New Words   Notes        Next >    |
+------------------------------------------------------+
```

The default state shows no glosses, translations, note text, or annotation marks.

### Segment Text

Renders the segment `text` exactly. Each token is clickable; punctuation renders as text but is not clickable.

Token interaction model:

```text
Displayed text:

  [孟子] [見] [梁惠王] 。 [王] [曰] ： [叟] ， [不遠] [千里] [而] [來] ...

Clickable tokens:

  [孟子]    token -> glossId
  [見]      token -> glossId
  [梁惠王]  token -> glossId

Punctuation:

  。 ： ，   rendered as text, not clickable tokens
```

## Gloss Behavior

Clicking a token opens the gloss for that specific token occurrence.

The gloss comes from the occurrence's `glossId`, not a lookup by surface, because one character can have several senses.

**New Words** reveals the segment's `newGlossIds`: glosses whose first occurrence in document order is this segment (content-defined, not per-user).

Single-token gloss popover:

```text
+------------------------------------------------------+
| 三國志                                      卷一      |
+------------------------------------------------------+
|                                                      |
|          [孟子]見梁惠王。                            |
|             |                                        |
|             v                                        |
|          +----------------------+                    |
|          | 孟子                 |                    |
|          | Mengzi               |                    |
|          | Mencius              |                    |
|          +----------------------+                    |
|                                                      |
+------------------------------------------------------+
|  < Previous        New Words   Notes        Next >    |
+------------------------------------------------------+
```

New glosses for current segment:

```text
+------------------------------------------------------+
| 三國志                                      卷一      |
+------------------------------------------------------+
|                                                      |
|          孟子見梁惠王。                              |
|          王曰：叟，不遠千里而來，                    |
|          亦將有以利吾國乎？                          |
|                                                      |
+---------------- New Words In This Segment -----------+
| 孟子      Mengzi       Mencius                        |
| 梁惠王    Liang Huiwang King Hui of Liang             |
| 叟        sou          old man; elder                 |
+------------------------------------------------------+
|  < Previous        Hide Words  Notes        Next >     |
+------------------------------------------------------+
```

## Notes Behavior

Notes are hidden by default. **Notes** shows subtle anchors on annotated spans; selecting one opens the note. Grammar notes explain constructions; context notes explain historical, literary, biographical, geographic, or interpretive background.

Notes-enabled layout:

```text
+------------------------------------------------------+
| 三國志                                      卷一      |
+------------------------------------------------------+
|                                                      |
|          孟子見梁惠王。                              |
|          王曰：叟，不遠千里而來，                    |
|          亦將有以利吾國乎？                          |
|                 ^ context                            |
|                         ^ grammar                    |
|                                                      |
+------------------------------------------------------+
|  < Previous        New Words   Hide Notes   Next >     |
+------------------------------------------------------+
```

Selected note layout:

```text
+------------------------------------------------------+
| 三國志                                      卷一      |
+------------------------------------------------------+
|                                                      |
|          孟子見梁惠王。                              |
|          王曰：叟，不遠千里而來，                    |
|          亦將有以利吾國乎？                          |
|                                                      |
+---------------- Context Note ------------------------+
| This opening frames the ruler's concern with profit, |
| setting up Mencius' response about benevolence and   |
| righteousness.                                      |
+------------------------------------------------------+
|  < Previous        New Words   Hide Notes   Next >     |
+------------------------------------------------------+
```

## Local User State

None in the first stage: no reading progress, last position, opened glosses or notes, or per-user "seen" state. The current position lives in the URL; without one, open the document or chapter start.

## Open Questions For Later

- Should note anchors be visible only after a notes toggle, or should there be a subtle always-available affordance?
- Should the reader show pinyin in the gloss popover by default, or behind an additional reveal?
- Should there be keyboard navigation for book-like reading?
