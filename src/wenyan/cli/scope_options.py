from __future__ import annotations

from typing import Annotated

import typer

from wenyan.cli.options import CHAPTER_REF_HELP, PARAGRAPH_REF_HELP, SEGMENT_REF_HELP

ChapterOption = Annotated[
    str | None,
    typer.Option("--chapter", help=CHAPTER_REF_HELP),
]
RequiredChapterOption = Annotated[
    str,
    typer.Option("--chapter", help=CHAPTER_REF_HELP),
]
ParagraphOption = Annotated[
    str | None,
    typer.Option("--paragraph", help=PARAGRAPH_REF_HELP),
]
RequiredParagraphOption = Annotated[
    str,
    typer.Option("--paragraph", help=PARAGRAPH_REF_HELP),
]
SegmentOption = Annotated[
    str,
    typer.Option("--segment", help=SEGMENT_REF_HELP),
]
OptionalSegmentOption = Annotated[
    str | None,
    typer.Option("--segment", help=SEGMENT_REF_HELP),
]
