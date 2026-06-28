import codecs
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from wenyan_models.artifacts.normalized import TextByteIndex
from wenyan_models.domain.ids import ContentHash, parse_content_hash


@dataclass(frozen=True)
class StreamNormalizationResult:
    source_hash: ContentHash
    normalized_hash: ContentHash
    character_count: int
    text_index: TextByteIndex


def normalize_source_to_file(
    source_path: Path,
    output_path: Path,
    *,
    index_stride: int = 65_536,
) -> StreamNormalizationResult:
    if index_stride <= 0:
        raise ValueError("index stride must be positive")
    source_hasher = hashlib.sha256()
    normalized_hasher = hashlib.sha256()
    byte_offsets = [0]
    char_count = 0
    pending = ""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f"{output_path.name}.tmp")
    try:
        with source_path.open("rb") as source, temp_path.open("wb") as destination:
            decoder = codecs.getincrementaldecoder("utf-8")()
            while True:
                raw = source.read(1024 * 1024)
                final = not raw
                if raw:
                    source_hasher.update(raw)
                if not raw and final:
                    break
                chunk = decoder.decode(raw, final=final)
                normalized, pending = _normalize_chunk(chunk, pending)
                char_count = _append_normalized_text(
                    destination,
                    normalized,
                    normalized_hasher,
                    char_count,
                    index_stride,
                    byte_offsets,
                )
            if pending:
                char_count = _append_normalized_text(
                    destination,
                    "\n",
                    normalized_hasher,
                    char_count,
                    index_stride,
                    byte_offsets,
                )
            if char_count == 0 or not _ends_with_newline(temp_path):
                char_count = _append_normalized_text(
                    destination,
                    "\n",
                    normalized_hasher,
                    char_count,
                    index_stride,
                    byte_offsets,
                )
        os.replace(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return StreamNormalizationResult(
        source_hash=parse_content_hash(f"sha256:{source_hasher.hexdigest()}"),
        normalized_hash=parse_content_hash(f"sha256:{normalized_hasher.hexdigest()}"),
        character_count=char_count,
        text_index=TextByteIndex(stride=index_stride, byte_offsets=tuple(byte_offsets)),
    )


def _normalize_chunk(chunk: str, pending: str) -> tuple[str, str]:
    combined = pending + chunk
    pending_out = ""
    if combined.endswith("\r"):
        pending_out = "\r"
        combined = combined[:-1]
    normalized = combined.replace("\r\n", "\n").replace("\r", "\n")
    return normalized, pending_out


def _append_normalized_text(
    destination,
    normalized: str,
    normalized_hasher,
    char_count: int,
    index_stride: int,
    byte_offsets: list[int],
) -> int:
    if not normalized:
        return char_count
    encoded = normalized.encode("utf-8")
    base_byte = destination.tell()
    destination.write(encoded)
    normalized_hasher.update(encoded)
    next_boundary = _next_index_boundary(char_count, index_stride)
    while next_boundary <= char_count + len(normalized):
        prefix = normalized[: next_boundary - char_count]
        byte_offsets.append(base_byte + len(prefix.encode("utf-8")))
        next_boundary += index_stride
    return char_count + len(normalized)


def _next_index_boundary(char_count: int, index_stride: int) -> int:
    if char_count == 0:
        return index_stride
    remainder = char_count % index_stride
    if remainder == 0:
        return char_count + index_stride
    return char_count + (index_stride - remainder)


def _ends_with_newline(path: Path) -> bool:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        if size == 0:
            return False
        handle.seek(-1, os.SEEK_END)
        return handle.read(1) == b"\n"
