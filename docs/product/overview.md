# Product Overview

> **Product** — what Wenyan Reader is and the principles behind it.

Wenyan Reader helps English-speaking learners read Classical Chinese (文言文) texts. Readers move through a document one bite-sized segment at a time and reveal glosses or notes only when they need help.

There are two parts:

| Part | Users | State |
|---|---|---|
| **Reader app** — local web app that displays packaged documents | students | not built; UX in [Reader UX](reader-ux.md) |
| **Preprocessing pipeline** — `wenyan` CLI plus agent skills that turn a full source text into a reader package | editors | working through packaging; context notes are agent-driven |

## Principles

- **No LLM at read time.** LLMs assist preprocessing only. The reader consumes validated local files.
- **Full documents.** A source is always a complete document; it is split into chapters, paragraphs, and segments for processing.
- **LLMs decide content, code decides structure.** Boundaries, tokens, glosses, and notes are content decisions. Code owns hashes, validation, assembly, packaging, and status.
- **Small, resumable units.** Each segment's jobs run and rerun independently; one bad gloss does not redo the paragraph.
- **Auditable artifacts.** Every intermediate result is a committed file. Status is derived from those files, so deleting a file rejects it.
- **Reviews are separate from drafts.** Each draft is checked by a separate review pass before it reaches the reader.
- **Quiet reading.** Help is on demand; the default view is just the text.

## Content model

| Unit | Meaning |
|---|---|
| document | Canonical source and content unit (e.g. 孫子兵法). |
| chapter | Top-level structural division (e.g. 始計第一). |
| paragraph | Unit for context framing and segment discovery. |
| segment | What the reader sees at once, and the smallest unit preprocessed — usually one sentence. |
| token | A clickable, glossable span within a segment. |
| gloss | One sense of a surface form: pinyin plus English. Tokens point to a gloss by id. |
| note | A grammar or context explanation anchored to tokens. |

Full vocabulary: [Glossary](../glossary.md).

## Where to go next

- How editors use the pipeline: [Editor Guide](editor-guide.md)
- What the pipeline does: [Pipeline](../spec/pipeline.md)
- Reader file format: [Reader Package](../spec/reader-package.md)
