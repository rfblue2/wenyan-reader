# Glossary

Canonical terms. Other docs link here rather than redefine them.

## Content

| Term | Meaning |
|---|---|
| **document** | The canonical source and content unit: one complete text (e.g. 孫子兵法). Never an excerpt. |
| **chapter** | Top-level structural division of a document. Boundaries are agreed by the editor and an agent. |
| **paragraph** | Structural unit within a chapter, used for context framing and segment discovery. |
| **segment** | The text shown to the reader at once (usually one sentence) and the smallest unit preprocessed. |
| **token** | A glossable span of a segment with `start`/`end` offsets. Punctuation is never a token. |
| **surface** | The written characters of a token or gloss entry. |
| **gloss** | One sense of a surface: `surface`, `pinyin`, English `gloss`, and an id. A surface can have several glosses. |
| **new gloss** | A gloss first introduced by a segment, listed in `newGlossIds`. Content-defined, not per-reader. |
| **grammar note** | Explanation of a Classical Chinese construction, anchored to tokens. No sources. |
| **context note** | Historical, literary, or interpretive background anchored to tokens, with citations for claims. |
| **paragraph context note** | A context note drafted with the paragraph and anchored to segments; attached to a token at assembly. |

## Preprocessing

| Term | Meaning |
|---|---|
| **artifact** | An intermediate preprocessing file under `preprocess/`, kept for auditability, validation, reruns, and packaging. |
| **reader package** | The validated files under `content/` that the reader loads. |
| **component** | One of the eight per-segment jobs: tokenize, gloss, grammar, context, and a review for each. |
| **draft** | A component output produced by an LLM or agent (tokenization, glosses, grammar notes, context notes). |
| **review** | A pass that approves or rejects one draft, writing `*-review.json`. |
| **assembly** | Deterministic compile of a paragraph's segment outputs into the reader paragraph shape. |
| **packaging** | Promoting assembled paragraphs to `content/` with the manifest, chapter files, and gloss index. |
| **glossary draft** | `indexes/glossary-draft.json`, the document glossary built from approved gloss reviews. |
| **candidate glosses** | Existing glossary entries offered to the gloss job for reuse. |
| **input hash** | `sha256:` hash of a job's inputs stored on its artifact; equal hash means the job skips. |
| **skill** | Agent instructions under `.opencode/skills/` for interactive or research-heavy steps. |
| **editor** | The developer or maintainer running the pipeline and reviewing output. Also `model: "editor"` on hand-written artifacts. |

## Status values

| Value | Meaning |
|---|---|
| `pending` | Output missing (or upstream not ready). |
| `in-progress` | Some but not all children complete. |
| `complete` | Output present (and, for reviews, approved). |
| `blocked` | A review rejected the output. |
| `stale` | Output exists but its inputs changed. Produced only for paragraph assembly. |
| `failed` | Defined but not produced today. |

Rules: [Artifacts — Effective status](spec/artifacts.md#effective-status).
