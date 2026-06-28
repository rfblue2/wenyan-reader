from wenyan.core.adapters.anthropic_llm_client import AnthropicLLMClient
from wenyan_models.config import RetryConfig

MINIMAX_ANTHROPIC_BASE_URL = "https://api.minimax.io/anthropic"


class MiniMaxLLMClient(AnthropicLLMClient):
    """MiniMax via their Anthropic-compatible API (recommended by MiniMax)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        retry: RetryConfig | None = None,
    ) -> None:
        super().__init__(
            api_key,
            model,
            base_url=MINIMAX_ANTHROPIC_BASE_URL,
            retry=retry,
        )
