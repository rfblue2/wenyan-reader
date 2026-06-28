from pathlib import Path

import pytest

from wenyan.core.adapters.yaml_source_registry import YamlSourceRegistry
from wenyan_models.domain.ids import document_id, slug


def test_resolve_slug(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    registry = YamlSourceRegistry(tmp_path)

    entry = registry.resolve("sunzi-bingfa")

    assert entry.slug == "sunzi-bingfa"
    assert entry.title == "孙子兵法"
    assert entry.document_id is None


def test_assign_and_resolve_document_id(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    registry = YamlSourceRegistry(tmp_path)
    doc = document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")

    registry.assign_document_id(slug("sunzi-bingfa"), doc)
    entry = registry.resolve("sunzi-bingfa")

    assert entry.document_id == doc
    assert registry.resolve(str(doc)).document_id == doc


def test_resolve_unknown_raises(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    registry = YamlSourceRegistry(tmp_path)

    with pytest.raises(ValueError, match="not found"):
        registry.resolve("missing")


def test_load_document_yaml(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    _write_document_yaml(tmp_path)
    registry = YamlSourceRegistry(tmp_path)

    doc_yaml = registry.load_document_yaml(slug("sunzi-bingfa"))

    assert doc_yaml.title == "孙子兵法"


def _write_registry(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "registry.yaml").write_text(
        "documents:\n"
        "  - slug: sunzi-bingfa\n"
        "    title: 孙子兵法\n"
        "    status: active\n",
        encoding="utf-8",
    )


def _write_document_yaml(tmp_path: Path) -> None:
    doc_dir = tmp_path / "sources" / "documents" / "sunzi-bingfa"
    doc_dir.mkdir(parents=True)
    (doc_dir / "document.yaml").write_text(
        "title: 孙子兵法\nlanguage: zh-Hant\n",
        encoding="utf-8",
    )
