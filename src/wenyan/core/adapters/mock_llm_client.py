import json
import re
import uuid
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from wenyan.core.adapters.prompt_template import RenderedPrompt
from wenyan.core.ports.llm_client import LLMClient, StructuredPrompt
from wenyan_models.artifacts.paragraph import ParagraphDraft, ParagraphDraftSegment
from wenyan_models.artifacts.segment import TokenizationArtifact
from wenyan_models.artifacts.structure import ChapterProposal, ChapterProposalItem, ParagraphProposal, ParagraphProposalItem
from wenyan_models.domain.ids import (
    chapter_id,
    paragraph_id,
    segment_id,
)
from wenyan_models.text.tokenization import drop_punctuation_tokens


class LLMParseError(RuntimeError):
    pass


class MockLLMClient(LLMClient):
    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T:
        name = prompt.template_name
        if name == "chapter-structure":
            return self._chapter_proposal(prompt, model)
        if name == "paragraph-structure":
            return self._paragraph_proposal(prompt, model)
        if name == "paragraph-segmentation":
            return self._paragraph_draft(prompt, model)
        if name == "segment-tokenization":
            return self._tokenization(prompt, model, "segment-tokenization.json")
        if name == "segment-tokenization-review":
            return self._tokenization_review(prompt, model, "segment-tokenization-review.json")
        if name == "segment-gloss":
            return self._glosses(prompt, model)
        if name == "segment-gloss-review":
            return self._gloss_review(prompt, model)
        if name == "segment-grammar":
            return self._grammar_notes(prompt, model)
        if name == "segment-grammar-review":
            return self._grammar_review(prompt, model)
        if name == "segment-context":
            return self._context_notes(prompt, model)
        if name == "segment-context-review":
            return self._context_review(prompt, model)
        fixture_path = self._fixture_dir / f"{name}.json"
        if not fixture_path.is_file():
            raise LLMParseError(f"no fixture for prompt template: {name}")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return TypeAdapter(model).validate_python(payload)

    def _chapter_proposal[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        if isinstance(prompt, RenderedPrompt):
            text = prompt.context_value("document_text")
            rendered = prompt.render({})
        else:
            rendered = prompt.render({})
            text = _extract_section(rendered, "Document text:", "DOCUMENT_ID:")
        chapters: list[ChapterProposalItem] = []
        for match in re.finditer(r"(?m)^(.+第[一二三四五六七八九十百千]+)$", text):
            start = match.start()
            title = match.group(1)
            chapters.append(
                ChapterProposalItem(
                    id=chapter_id(str(uuid.uuid4())),
                    title=title,
                    start=start,
                    end=start,
                    rationale="source heading",
                ),
            )
        for index, chapter in enumerate(chapters):
            end = chapters[index + 1].start if index + 1 < len(chapters) else len(text)
            chapters[index] = chapter.model_copy(update={"end": end})
        rendered = prompt.render({})
        proposal = ChapterProposal.model_validate(
            {
                "documentId": _context_value(rendered, "document_id"),
                "model": "mock",
                "inputHash": _context_value(rendered, "input_hash"),
                "attempts": 1,
                "sourceHash": _context_value(rendered, "source_hash"),
                "chapters": [chapter.model_dump(by_alias=True) for chapter in chapters],
            },
        )
        return proposal  # type: ignore[return-value]

    def _paragraph_proposal[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        if isinstance(prompt, RenderedPrompt):
            text = prompt.context_value("chapter_text")
            rendered = prompt.render({})
        else:
            rendered = prompt.render({})
            text = _extract_section(rendered, "Chapter text:", "DOCUMENT_ID:")
        paragraphs = _paragraph_spans_from_blank_lines(text)
        proposal = ParagraphProposal.model_validate(
            {
                "documentId": _context_value(rendered, "document_id"),
                "chapterId": _context_value(rendered, "chapter_id"),
                "model": "mock",
                "inputHash": _context_value(rendered, "input_hash"),
                "attempts": 1,
                "chapterTextHash": _context_value(rendered, "chapter_text_hash"),
                "paragraphs": [item.model_dump(by_alias=True) for item in paragraphs],
            },
        )
        return proposal  # type: ignore[return-value]

    def _paragraph_draft[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        if isinstance(prompt, RenderedPrompt):
            text = prompt.context_value("paragraph_text")
            rendered = prompt.render({})
        else:
            rendered = prompt.render({})
            text = _extract_section(rendered, "Paragraph text:", "PARAGRAPH_ID:")
        segments = _segments_from_sentences(text)
        draft = ParagraphDraft.model_validate(
            {
                "paragraphId": _context_value(rendered, "paragraph_id"),
                "model": "mock",
                "inputHash": _context_value(rendered, "input_hash"),
                "attempts": 1,
                "segments": [segment.model_dump(by_alias=True) for segment in segments],
            },
        )
        return draft  # type: ignore[return-value]

    def _tokenization[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
        fixture_name: str,
    ) -> T:
        fixture_path = self._fixture_dir / fixture_name
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
            payload["text"] = prompt.context_value("segment_text")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
            payload["text"] = _context_value(rendered, "segment_text")
        artifact = TypeAdapter(model).validate_python(payload)
        if isinstance(artifact, TokenizationArtifact):
            return artifact.model_copy(
                update={"tokens": drop_punctuation_tokens(artifact.tokens)},
            )  # type: ignore[return-value]
        return artifact

    def _tokenization_review[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
        fixture_name: str,
    ) -> T:
        fixture_path = self._fixture_dir / fixture_name
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
            payload["inputHash"] = prompt.context_value("review_input_hash")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
            payload["inputHash"] = _context_value(rendered, "review_input_hash")
        return TypeAdapter(model).validate_python(payload)

    def _glosses[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        if isinstance(prompt, RenderedPrompt):
            segment_id_value = prompt.context_value("segment_id")
            input_hash = prompt.context_value("input_hash")
            tokenization = json.loads(prompt.context_value("tokenization_json"))
            candidate_glosses = json.loads(prompt.context_value("candidate_glosses_json"))
        else:
            rendered = prompt.render({})
            segment_id_value = _context_value(rendered, "segment_id")
            input_hash = _context_value(rendered, "input_hash")
            tokenization = json.loads(_extract_section(rendered, "Tokenization:", "Candidate glosses:"))
            candidate_glosses = json.loads(
                _extract_section(rendered, "Candidate glosses:", "SEGMENT_ID:"),
            )
        candidates_by_key = {
            (
                entry["surface"],
                entry["pinyin"].strip().lower(),
                " ".join(entry["gloss"].strip().lower().split()),
            ): entry["id"]
            for entry in candidate_glosses
        }
        gloss_decisions: list[dict[str, str]] = []
        new_glosses: list[dict[str, str]] = []
        new_gloss_ids: list[str] = []
        for token in tokenization["tokens"]:
            surface = token["surface"]
            gloss_id = str(uuid.uuid4())
            entry = {
                "id": gloss_id,
                "surface": surface,
                "pinyin": surface.lower(),
                "gloss": f"gloss for {surface}",
            }
            key = (
                surface,
                entry["pinyin"].strip().lower(),
                " ".join(entry["gloss"].strip().lower().split()),
            )
            existing_id = candidates_by_key.get(key)
            if existing_id is not None:
                gloss_decisions.append(
                    {
                        "tokenId": token["id"],
                        "glossId": existing_id,
                        "decision": "reuse-existing",
                    },
                )
                continue
            gloss_decisions.append(
                {
                    "tokenId": token["id"],
                    "glossId": gloss_id,
                    "decision": "create-new",
                },
            )
            new_gloss_ids.append(gloss_id)
            new_glosses.append(entry)
            candidates_by_key[key] = gloss_id
        payload = {
            "segmentId": segment_id_value,
            "model": "mock",
            "inputHash": input_hash,
            "attempts": 1,
            "glossDecisions": gloss_decisions,
            "newGlossIds": new_gloss_ids,
            "newGlosses": new_glosses,
        }
        return TypeAdapter(model).validate_python(payload)

    def _gloss_review[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        fixture_path = self._fixture_dir / "segment-gloss-review.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
            payload["inputHash"] = prompt.context_value("review_input_hash")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
            payload["inputHash"] = _context_value(rendered, "review_input_hash")
        return TypeAdapter(model).validate_python(payload)

    def _grammar_notes[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        if isinstance(prompt, RenderedPrompt):
            segment_id_value = prompt.context_value("segment_id")
            input_hash = prompt.context_value("input_hash")
            tokenization = json.loads(prompt.context_value("tokenization_json"))
        else:
            rendered = prompt.render({})
            segment_id_value = _context_value(rendered, "segment_id")
            input_hash = _context_value(rendered, "input_hash")
            tokenization = json.loads(_extract_section(rendered, "Tokenization:", "Local context:"))
        grammar_notes: list[dict[str, object]] = []
        zhi_tokens = [token for token in tokenization["tokens"] if token["surface"] == "之"]
        if zhi_tokens:
            grammar_notes.append(
                {
                    "id": str(uuid.uuid4()),
                    "anchorTokenIds": [zhi_tokens[0]["id"]],
                    "body": "之 links the modifier to its head noun.",
                },
            )
        payload = {
            "segmentId": segment_id_value,
            "model": "mock",
            "inputHash": input_hash,
            "attempts": 1,
            "grammarNotes": grammar_notes,
        }
        return TypeAdapter(model).validate_python(payload)

    def _grammar_review[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        fixture_path = self._fixture_dir / "segment-grammar-review.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
            payload["inputHash"] = prompt.context_value("review_input_hash")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
            payload["inputHash"] = _context_value(rendered, "review_input_hash")
        return TypeAdapter(model).validate_python(payload)

    def _context_notes[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        if isinstance(prompt, RenderedPrompt):
            segment_id_value = prompt.context_value("segment_id")
            input_hash = prompt.context_value("input_hash")
        else:
            rendered = prompt.render({})
            segment_id_value = _context_value(rendered, "segment_id")
            input_hash = _context_value(rendered, "input_hash")
        payload = {
            "segmentId": segment_id_value,
            "model": "mock",
            "inputHash": input_hash,
            "attempts": 1,
            "contextNotes": [],
        }
        return TypeAdapter(model).validate_python(payload)

    def _context_review[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        fixture_path = self._fixture_dir / "segment-context-review.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
            payload["inputHash"] = prompt.context_value("review_input_hash")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
            payload["inputHash"] = _context_value(rendered, "review_input_hash")
        return TypeAdapter(model).validate_python(payload)


def _segments_from_sentences(text: str) -> tuple[ParagraphDraftSegment, ...]:
    stripped = text.strip()
    if not stripped:
        return (ParagraphDraftSegment(id=segment_id(str(uuid.uuid4())), text=text),)
    parts = [part for part in re.split(r"(?<=[。！？；])", stripped) if part]
    if not parts:
        return (ParagraphDraftSegment(id=segment_id(str(uuid.uuid4())), text=stripped),)
    return tuple(
        ParagraphDraftSegment(id=segment_id(str(uuid.uuid4())), text=part)
        for part in parts
    )


def _paragraph_spans_from_blank_lines(text: str) -> tuple[ParagraphProposalItem, ...]:
    lines = text.splitlines(keepends=True)
    paragraphs: list[ParagraphProposalItem] = []
    start = 0
    buffer = ""
    for line in lines:
        buffer += line
        if not line.strip():
            if buffer.strip():
                paragraphs.append(
                    ParagraphProposalItem(
                        id=paragraph_id(str(uuid.uuid4())),
                        start=start,
                        end=start + len(buffer),
                        rationale="blank-line paragraph",
                    ),
                )
            start += len(buffer)
            buffer = ""
    if buffer.strip():
        paragraphs.append(
            ParagraphProposalItem(
                id=paragraph_id(str(uuid.uuid4())),
                start=start,
                end=start + len(buffer),
                rationale="final paragraph",
            ),
        )
    if not paragraphs:
        paragraphs.append(
            ParagraphProposalItem(
                id=paragraph_id(str(uuid.uuid4())),
                start=0,
                end=len(text),
                rationale="single paragraph",
            ),
        )
    return tuple(paragraphs)


def _extract_section(rendered: str, heading: str, next_marker: str) -> str:
    if heading not in rendered:
        raise LLMParseError(f"missing section: {heading}")
    after_heading = rendered.split(heading, 1)[1].lstrip("\n")
    if next_marker not in after_heading:
        raise LLMParseError(f"missing marker: {next_marker}")
    return after_heading.split(next_marker, 1)[0].rstrip(" \t")


def _context_value(rendered: str, key: str) -> str:
    marker = f"{key.upper()}:"
    for line in rendered.splitlines():
        if line.startswith(marker):
            return line.removeprefix(marker).strip()
    raise LLMParseError(f"missing {key} in prompt context")
