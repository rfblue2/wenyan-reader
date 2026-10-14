from wenyan_models.artifacts.segment import GlossEntry, TokenizationArtifact


def filter_candidates_by_token_surfaces(
    candidates: tuple[GlossEntry, ...],
    tokenization: TokenizationArtifact,
) -> tuple[GlossEntry, ...]:
    surfaces = {token.surface for token in tokenization.tokens}
    return tuple(entry for entry in candidates if entry.surface in surfaces)
