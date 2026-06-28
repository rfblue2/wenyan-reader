import codecs
from pathlib import Path

from wenyan_models.artifacts.normalized import TextByteIndex


def read_text_slice(path: Path, index: TextByteIndex, start: int, end: int) -> str:
    if start < 0 or end < start:
        raise ValueError("invalid text slice bounds")
    if start == end:
        return ""
    stride = index.stride
    if stride <= 0:
        raise ValueError("text index stride must be positive")
    anchor_char = (start // stride) * stride
    anchor_index = start // stride
    if anchor_index >= len(index.byte_offsets):
        raise ValueError("text index does not cover requested slice")
    with path.open("rb") as handle:
        decoder = codecs.getincrementaldecoder("utf-8")()
        _, carry = _seek_char_position(
            handle,
            decoder,
            target_char=start,
            current_char=anchor_char,
            byte_offset=index.byte_offsets[anchor_index],
        )
        return _read_chars(handle, decoder, carry, end - start)


def _seek_char_position(
    handle,
    decoder: codecs.IncrementalDecoder,
    *,
    target_char: int,
    current_char: int,
    byte_offset: int,
) -> tuple[int, str]:
    handle.seek(byte_offset)
    carry = ""
    while current_char < target_char:
        raw = handle.read(65_536)
        if not raw:
            raise ValueError("normalized text ended before requested slice")
        text = carry + decoder.decode(raw, final=False)
        carry = ""
        remaining = target_char - current_char
        if len(text) <= remaining:
            current_char += len(text)
            continue
        carry = text[remaining:]
        current_char = target_char
    return current_char, carry


def _read_chars(handle, decoder: codecs.IncrementalDecoder, carry: str, length: int) -> str:
    if length <= 0:
        return ""
    parts: list[str] = []
    collected = 0
    if carry:
        if len(carry) >= length:
            return carry[:length]
        parts.append(carry)
        collected = len(carry)
    while collected < length:
        raw = handle.read(65_536)
        if not raw:
            text = decoder.decode(b"", final=True)
        else:
            text = decoder.decode(raw, final=False)
        if not text:
            break
        need = length - collected
        if len(text) <= need:
            parts.append(text)
            collected += len(text)
            continue
        parts.append(text[:need])
        break
    return "".join(parts)
