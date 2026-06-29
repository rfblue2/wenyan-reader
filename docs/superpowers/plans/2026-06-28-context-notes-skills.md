# Context Notes Skills Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CLI-driven context note jobs with two interactive Cursor skills; split grammar and context note schemas; stub context CLI commands; keep grammar CLI on the new `GrammarNoteItem` shape.

**Architecture:** Artifact models in `wenyan-models` first. Normalization and grammar jobs follow. Context jobs become thin stubs returning `JobFailure(code="not-implemented", …)` with skill paths. Skills write the same on-disk JSON the stubs no longer produce. Greenfield: delete only stale **note** artifacts (`*-notes.json`, `*-review.json` for grammar/context) — leave tokenization, glosses, and other segment files intact.

**Spec:** [2026-06-28-context-notes-skills-design.md](../specs/2026-06-28-context-notes-skills-design.md)

**Tech Stack:** Python 3.12+, uv, Typer, Pydantic v2, pytest, existing mock LLM for grammar tests only

## Global Constraints

- Run tests via `uv run python -m pytest` (never bare `python`).
- `mypy --strict` must pass on touched packages before each task commit.
- Context annotate/review job modules stay on disk; bodies become stubs (future CLI revival).
- Skill-written context artifacts use `model: "editor"`.
- No backward compatibility with `NoteItem`, `NoteSource`, `sourceSnippets`, or `candidateGlosses`.

---

## Task 1: Note models and `SegmentInput` trim

**Files:**
- Modify: `packages/wenyan-models/src/wenyan_models/artifacts/segment.py`
- Modify: `packages/wenyan-models/src/wenyan_models/show/segment.py`
- Test: `tests/core/notes/test_note_models.py` (create)

- [ ] **1.1** Replace `NoteSource` / `NoteItem` with:

```python
class GrammarNoteItem(BaseModel):
    id: str
    anchor_token_ids: tuple[str, ...] = Field(alias="anchorTokenIds")
    body: str

class NoteCitation(BaseModel):
    label: str
    excerpt: str
    url: str = ""
    accessed_at: str = Field(default="", alias="accessedAt")

class ContextNoteItem(BaseModel):
    id: str
    anchor_token_ids: tuple[str, ...] = Field(alias="anchorTokenIds")
    body: str
    sources: tuple[NoteCitation, ...] = ()
```

- [ ] **1.2** Update `GrammarNotesArtifact.grammar_notes` → `tuple[GrammarNoteItem, …]`; `ContextNotesArtifact.context_notes` → `tuple[ContextNoteItem, …]`.

- [ ] **1.3** Update `SourceGroundingItem`: replace `source_ids` / `sourceIds` with `source_indexes` / `sourceIndexes: tuple[int, …]`.

- [ ] **1.4** Remove `candidate_glosses` and `source_snippets` from `SegmentInput`.

- [ ] **1.5** Update show models:
  - `GrammarNoteShowItem` — `id`, `anchorTokenIds`, `anchorSurfaces`, `body` (no `type`, no `sources`)
  - `ContextNoteShowItem` — same + `sources: tuple[NoteCitationShowItem, …]`
  - `NoteCitationShowItem` — `url`, `label`, `excerpt`, `accessedAt`
  - Remove shared `NoteShowItem` / `NoteSourceShowItem` if replaced

- [ ] **1.6** Add `test_note_models.py`: validate example JSON from design spec parses; `extra: forbid` rejects `type`/`sources` on grammar notes.

- [ ] **1.7** Run: `uv run python -m pytest tests/core/notes/test_note_models.py -q`

**Commit:** `refactor(models): split grammar and context note types`

---

## Task 2: Normalization split

**Files:**
- Modify: `src/wenyan/core/notes/normalize_notes.py` → split or rename to `normalize_grammar_notes.py` + `normalize_context_notes.py`
- Modify: `tests/core/notes/test_normalize_notes.py`

- [ ] **2.1** `normalize_grammar_notes(notes, tokenization)` — drop notes with invalid anchors, empty body, duplicate ids. No source handling.

- [ ] **2.2** `normalize_context_notes(notes, tokenization)` — same anchor rules; drop citations missing `label` or `excerpt`; dedupe note ids.

- [ ] **2.3** Update tests: grammar path; context path with valid/invalid citations.

- [ ] **2.4** Run: `uv run python -m pytest tests/core/notes/ -q`

**Commit:** `refactor(notes): split grammar and context normalization`

---

## Task 3: Grammar job and prompt updates

**Files:**
- Modify: `src/wenyan/jobs/annotate_segment_grammar.py`
- Modify: `prompts/segment-grammar.md`
- Modify: `src/wenyan/core/adapters/mock_llm_client.py` (`_grammar_notes`)
- Modify: `tests/jobs/test_grammar_context_segment.py`

- [ ] **3.1** Import `normalize_grammar_notes`; remove `normalize_notes` usage.

- [ ] **3.2** Remove “Use `type` `grammar`” from `segment-grammar.md`.

- [ ] **3.3** Mock grammar payload: drop `type` and `sources` from generated notes.

- [ ] **3.4** Fix grammar tests: assert `GrammarNoteItem` shape (no `type`).

- [ ] **3.5** Run: `uv run python -m pytest tests/jobs/test_grammar_context_segment.py -q -k grammar`

**Commit:** `fix(grammar): use GrammarNoteItem in annotate job`

---

## Task 4: Gloss job — drop segment-input candidates

**Files:**
- Modify: `src/wenyan/jobs/gloss_segment.py`
- Test: existing gloss tests

- [ ] **4.1** Remove `segment_input.candidate_glosses` merge; use `load_candidate_glosses()` only.

- [ ] **4.2** Run: `uv run python -m pytest tests/jobs/test_gloss_segment.py -q`

**Commit:** `refactor(gloss): drop unused candidateGlosses from segment input`

---

## Task 5: Stub context jobs

**Files:**
- Modify: `src/wenyan/jobs/annotate_segment_context.py`
- Modify: `src/wenyan/jobs/review_segment_context.py`
- Modify: `tests/jobs/test_grammar_context_segment.py`

Constants (shared):

```python
_DRAFT_SKILL = ".cursor/skills/drafting-context-notes/SKILL.md"
_REVIEW_SKILL = ".cursor/skills/reviewing-context-notes/SKILL.md"
```

- [ ] **5.1** `run_annotate_segment_context` → immediate `JobFailure(code="not-implemented", message=f"Context drafting is skill-driven; see {_DRAFT_SKILL}")`. Keep function signature and exports.

- [ ] **5.2** `run_review_segment_context` → same with `_REVIEW_SKILL`.

- [ ] **5.3** Replace context tests with stub expectations (non-zero exit, message contains skill path). Keep grammar tests from Task 3.

- [ ] **5.4** Run: `uv run python -m pytest tests/jobs/test_grammar_context_segment.py -q`

**Commit:** `feat(context): stub annotate/review jobs; point to skills`

---

## Task 6: Show layer and CLI output

**Files:**
- Modify: `src/wenyan/core/show/segment_view.py`
- Modify: `src/wenyan/cli/show_output.py`
- Modify: `tests/cli/test_show_output.py`

- [ ] **6.1** Load `GrammarNoteItem` / `ContextNoteItem` separately in segment view builders.

- [ ] **6.2** Map to `GrammarNoteShowItem` / `ContextNoteShowItem` (resolve `anchorSurfaces` from tokenization).

- [ ] **6.3** Update `show_output.py` context review display: `sourceIndexes` instead of `sourceIds`.

- [ ] **6.4** Update show tests with new note/citation JSON.

- [ ] **6.5** Run: `uv run python -m pytest tests/cli/test_show_output.py -q`

**Commit:** `fix(show): grammar and context note display types`

---

## Task 7: Prompt template tests and misc references

**Files:**
- Modify: `tests/prompts/test_prompt_templates.py`
- Grep and fix any remaining `NoteItem` / `NoteSource` / `sourceSnippets` / `candidateGlosses` imports

- [ ] **7.1** Remove or narrow context prompt template tests (prompts remain on disk but unused).

- [ ] **7.2** Fix any broken imports across `tests/` and `src/`.

- [ ] **7.3** Run full suite: `uv run python -m pytest -q` (bounded; fix failures).

**Commit:** `chore: fix references after note model split`

---

## Task 8: Greenfield note artifact cleanup

**Scope:** Delete **note artifacts only** — not tokenization, glosses, `input.json`, or other segment job files.

**Delete per segment** (under `preprocess/documents/*/jobs/segments/<segment-id>/`):

- `grammar-notes.json`
- `grammar-review.json`
- `context-notes.json`
- `context-review.json`

**Do not delete:** `input.json`, `tokenization.json`, `tokenization-review.json`, `glosses.json`, `gloss-review.json`, paragraph drafts, structure, normalized text, etc.

**Optional:** If any `input.json` still has `candidateGlosses` / `sourceSnippets` keys, remove those keys when touched — or delete and regenerate `input.json` via `split-segments --force` only if validation fails after Task 1.

- [ ] **8.1** Remove the four note artifact files listed above under `preprocess/documents/`.

- [ ] **8.2** Editors re-run grammar CLI for segments that need grammar notes; use skills for context notes.

**Commit:** `chore: remove stale segment note artifacts`

---

## Task 9: Architecture and AGENTS docs

**Files:**
- Modify: `architecture/preprocessing/source-grounding.md`
- Modify: `architecture/preprocessing/intermediate-artifacts.md`
- Modify: `architecture/storage-format.md`
- Modify: `architecture/cli-spec.md`
- Modify: `AGENTS.md`

- [ ] **9.1** Document inline `NoteCitation` on context notes; no segment-input snippets.

- [ ] **9.2** Update segment input example (drop `candidateGlosses`, `sourceSnippets`).

- [ ] **9.3** Mark context CLI commands as stubbed; reference both skills.

- [ ] **9.4** AGENTS.md: context notes via skills, not CLI.

**Commit:** `docs: context notes skills and note schema`

---

## Task 10: Skill — drafting context notes

**Files:**
- Create: `.cursor/skills/drafting-context-notes/SKILL.md`
- Optional: `.cursor/skills/drafting-context-notes/artifact-example.json`

- [ ] **10.1** Frontmatter `name` / `description` per preparing-source-structure pattern.

- [ ] **10.2** Workflow: prerequisites, reads, web research, drafting rules, artifact field table (`model: "editor"`, `inputHash` formula).

- [ ] **10.3** Include full `ContextNoteItem` / `NoteCitation` JSON example matching Pydantic schema.

- [ ] **10.4** End with `validate-artifacts` and `show` inspection steps.

**Commit:** `docs(skill): add drafting-context-notes`

---

## Task 11: Skill — reviewing context notes

**Files:**
- Create: `.cursor/skills/reviewing-context-notes/SKILL.md`
- Optional: `.cursor/skills/reviewing-context-notes/artifact-example.json`

- [ ] **11.1** Review checklist (grounding, anchors, duplication, gloss conflicts).

- [ ] **11.2** Write-only `context-review.json`; rejection findings shape; `sourceGrounding` with `sourceIndexes`.

- [ ] **11.3** `inputHash` = sha256 of `context-notes.json` file content (document exact command or use existing hashing helper pattern from jobs).

- [ ] **11.4** On reject: re-run draft skill; never edit notes in review skill.

**Commit:** `docs(skill): add reviewing-context-notes`

---

## Task 12: Update preprocessing-segments skill

**Files:**
- Modify: `.cursor/skills/preprocessing-segments/SKILL.md`

- [ ] **12.1** Mark `annotate-segment-context` / `review-segment-context` as skill-driven (not CLI).

- [ ] **12.2** Document `run` stopping at context with skill pointer.

- [ ] **12.3** Link to drafting and reviewing context skills in workflow checklist.

**Commit:** `docs(skill): preprocessing-segments context handoff`

---

## Task 13: Final verification

- [ ] **13.1** `uv run python -m pytest -q`
- [ ] **13.2** `uv run mypy` (or project-standard typecheck command)
- [ ] **13.3** Manual smoke:
  - `uv run wenyan preprocess annotate-segment-context <slug> --segment <id>` → not-implemented + skill path
  - `uv run wenyan preprocess run <slug>` → stops at context stage with same pointer when grammar complete

**Commit (if fixes needed):** `fix: context notes skills slice cleanup`

---

## Dependency Graph

```text
Task 1 (models)
  → Task 2 (normalize)
  → Task 3 (grammar job)
  → Task 4 (gloss)
  → Task 5 (context stubs)
  → Task 6 (show)
  → Task 7 (test sweep)
  → Task 8 (delete note artifacts only)  # after Task 1
  → Task 9–12 (docs + skills)   # can parallel after Task 5
  → Task 13 (verify)
```

## Out of Scope (this plan)

- Restoring LLM context annotate/review CLI
- Multi-turn web search in `AnthropicLLMClient`
- Paragraph-level `paragraphContextNotes` schema change
- Committing regenerated Sunzi segment artifacts after skill use
