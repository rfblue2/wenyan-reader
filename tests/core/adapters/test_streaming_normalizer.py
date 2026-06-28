from pathlib import Path

from wenyan.core.adapters.streaming_normalizer import normalize_source_to_file
from wenyan.core.adapters.text_slice import read_text_slice
from wenyan_models.artifacts.normalized import TextByteIndex


def test_normalize_and_read_slices(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("abc\r\ndef\rghi", encoding="utf-8")
    output = tmp_path / "normalized-text.txt"
    result = normalize_source_to_file(source, output, index_stride=2)
    assert result.character_count == len("abc\ndef\nghi\n")
    assert output.read_text(encoding="utf-8") == "abc\ndef\nghi\n"
    index = result.text_index
    assert read_text_slice(output, index, 0, 3) == "abc"
    assert read_text_slice(output, index, 4, 7) == "def"
    assert read_text_slice(output, index, 8, 11) == "ghi"


def test_read_slice_with_sparse_index(tmp_path: Path) -> None:
    text = "x" * 100_000 + "target"
    path = tmp_path / "large.txt"
    path.write_text(text, encoding="utf-8")
    index = TextByteIndex(stride=65_536, byte_offsets=(0, 65_536))
    assert read_text_slice(path, index, 100_000, 100_006) == "target"
