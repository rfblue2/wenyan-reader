from pathlib import Path

from wenyan.core.adapters.mock_llm_client import MockLLMClient
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan_models.artifacts.structure import ChapterProposal


def test_mock_returns_chapter_proposal(tmp_path: Path) -> None:
  prompts = tmp_path / "prompts"
  prompts.mkdir()
  (prompts / "chapter-structure-v1.md").write_text(
      "Document text:\n{{document_text}}\n\n"
      "DOCUMENT_ID: {{document_id}}\n"
      "INPUT_HASH: {{input_hash}}\n"
      "SOURCE_HASH: {{source_hash}}\n",
      encoding="utf-8",
  )
  template = load_prompt_template(prompts, "chapter-structure", "v1")
  context = {
      "document_text": "始計第一\n\n正文\n\n作戰第二\n\n更多",
      "document_id": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
      "input_hash": "sha256:abc",
      "source_hash": "sha256:def",
  }
  client = MockLLMClient(tmp_path / "fixtures")
  (tmp_path / "fixtures").mkdir()
  proposal = client.complete_model(RenderedPrompt(template, context), ChapterProposal)
  assert len(proposal.chapters) == 2
