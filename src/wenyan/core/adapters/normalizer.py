from wenyan.core.adapters.hashing import sha256_text
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.domain.ids import DocumentId
from wenyan_models.sources import DocumentYaml


def normalize_document(
    document_id: DocumentId,
    title: str,
    source_text: str,
    metadata: DocumentYaml,
) -> NormalizedDocument:
    normalized_text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_text.endswith("\n"):
        normalized_text += "\n"
    punctuation_policy = "preserve-source"
    if metadata.normalization:
        punctuation_policy = str(metadata.normalization.get("punctuationPolicy", punctuation_policy))
    encoding = "utf-8"
    if metadata.normalization:
        encoding = str(metadata.normalization.get("encoding", encoding))
    return NormalizedDocument.model_validate(
        {
            "documentId": str(document_id),
            "title": title,
            "sourceHash": str(sha256_text(source_text)),
            "normalizedHash": str(sha256_text(normalized_text)),
            "text": normalized_text,
            "normalization": {
                "encoding": encoding,
                "punctuationPolicy": punctuation_policy,
                "notes": [],
            },
        },
    )
