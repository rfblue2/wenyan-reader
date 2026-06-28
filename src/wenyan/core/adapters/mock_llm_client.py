import json
import re
import uuid
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from wenyan.core.adapters.prompt_template import RenderedPrompt
from wenyan.core.ports.llm_client import StructuredPrompt
from wenyan_models.artifacts.paragraph import ParagraphDraft, ParagraphDraftSegment
from wenyan_models.artifacts.structure import ChapterProposal, ChapterProposalItem, ParagraphProposal, ParagraphProposalItem
from wenyan_models.domain.ids import (
    chapter_id,
    paragraph_id,
    segment_id,
)


class LLMParseError(RuntimeError):
    pass


class MockLLMClient:
    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T:
        version = str(prompt.prompt_version)
        if version == "chapter-structure-v1":
            return self._chapter_proposal(prompt, model)
        if version == "paragraph-structure-v1":
            return self._paragraph_proposal(prompt, model)
        if version == "paragraph-segmentation-v1":
            return self._paragraph_draft(prompt, model)
        if version == "segment-tokenization-v1":
            return self._tokenization(prompt, model)
        if version == "segment-tokenization-review-v1":
            return self._tokenization_review(prompt, model)
        fixture_path = self._fixture_dir / f"{version}.json"
        if not fixture_path.is_file():
            raise LLMParseError(f"no fixture for prompt version: {version}")
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
                "promptVersion": "chapter-structure-v1",
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
                "promptVersion": "paragraph-structure-v1",
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
        segments = tuple(
            ParagraphDraftSegment(id=segment_id(str(uuid.uuid4())), text=line)
            for line in text.splitlines()
            if line.strip()
        ) or (ParagraphDraftSegment(id=segment_id(str(uuid.uuid4())), text=text),)
        draft = ParagraphDraft.model_validate(
            {
                "paragraphId": _context_value(rendered, "paragraph_id"),
                "model": "mock",
                "promptVersion": "paragraph-segmentation-v1",
                "inputHash": _context_value(rendered, "input_hash"),
                "attempts": 1,
                "segments": [segment.model_dump(by_alias=True) for segment in segments],
            },
        )
        return draft  # type: ignore[return-value]

    def _tokenization[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        fixture_path = self._fixture_dir / "segment-tokenization-v1.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
            payload["text"] = prompt.context_value("segment_text")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
            payload["text"] = _context_value(rendered, "segment_text")
        return TypeAdapter(model).validate_python(payload)

    def _tokenization_review[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T:
        fixture_path = self._fixture_dir / "segment-tokenization-review-v1.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        if isinstance(prompt, RenderedPrompt):
            payload["segmentId"] = prompt.context_value("segment_id")
        else:
            rendered = prompt.render({})
            payload["segmentId"] = _context_value(rendered, "segment_id")
        return TypeAdapter(model).validate_python(payload)


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
