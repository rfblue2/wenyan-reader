# App UX

## Purpose

Define the student-facing reading experience for the Classical Chinese reader.

The app should prioritize uninterrupted reading. Glosses, grammar notes, and context notes exist to support comprehension, but they should not dominate the page or become the default reading mode.

## Core Principles

- Show a bite-sized text segment by default.
- Keep the main reading surface visually quiet.
- Let the reader request help only when needed.
- Preserve access to all glosses and notes wherever they appear.
- Avoid turning the reader into an interlinear translation or study worksheet.

## Primary Views

### Library View

Shows the available curated documents.

Minimum required information:

- Document title.

Low-fidelity layout:

```text
+------------------------------------------------------+
| Classical Chinese Reader                             |
+------------------------------------------------------+
|                                                      |
|  Documents                                           |
|                                                      |
|  +------------------------------------------------+  |
|  | 三國志                                          |  |
|  +------------------------------------------------+  |
|                                                      |
|  +------------------------------------------------+  |
|  | 史記                                            |  |
|  +------------------------------------------------+  |
|                                                      |
+------------------------------------------------------+
```

### Reader View

Shows the current text segment and reading controls.

Core elements:

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

The default state should not show glosses, translations, note text, or visible annotation clutter.

### Segment Text

Renders the Classical Chinese text while preserving the original segment string.

Each glossable token should be clickable. Punctuation and non-glossable separators should render as part of the text but should not behave like tokens.

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

The displayed gloss comes from the token occurrence's `glossId`, not from a raw lookup by surface form. This is necessary because the same written form may have different meanings in different contexts.

The reader should also provide a way to reveal glosses first introduced by the current segment. A gloss is considered new if the current segment is its first canonical occurrence in the document, based on content order, not saved user history.

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

Grammar and context notes should be hidden by default.

When notes are enabled, the app may show subtle anchors on the relevant text span. Selecting an anchor opens the associated note.

Grammar notes explain salient Classical Chinese constructions. Context notes explain historical, literary, biographical, geographic, or interpretive context needed to understand the passage.

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

The first-stage app should not store local user state.

Do not persist:

- Reading progress.
- Last-opened document, chapter, paragraph, or segment.
- Glosses the reader has opened.
- Notes the reader has opened.
- Per-user seen or introduced status.

The current reading position can be represented by the route or URL while the app is open. If the page is reloaded without a segment in the URL, the app can return to the document or chapter start.

Important distinctions:

- A reader can always click any token and see its gloss.
- A gloss can be listed as new for a segment when that segment contains the first canonical occurrence of its `glossId` in the document.
- Notes remain available from the segment that contains them, without tracking whether the reader has seen them.

## Open Questions For Later

- Should note anchors be visible only after a notes toggle, or should there be a subtle always-available affordance?
- Should the reader show pinyin in the gloss popover by default, or behind an additional reveal?
- Should there be keyboard navigation for book-like reading?
