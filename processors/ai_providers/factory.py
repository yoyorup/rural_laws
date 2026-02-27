"""Registry and factory for AI providers."""

from processors.ai_providers.base import BaseAIProvider
from processors.ai_providers.claude_provider import ClaudeProvider
from processors.ai_providers.openai_provider import OpenAIProvider
from processors.ai_providers.qwen_provider import QwenProvider
from processors.ai_providers.glm_provider import GLMProvider
from processors.ai_providers.gemini_provider import GeminiProvider

REGISTRY: dict[str, type[BaseAIProvider]] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "qwen": QwenProvider,
    "glm": GLMProvider,
    "gemini": GeminiProvider,
}


def get_provider(name: str = None) -> BaseAIProvider:
    """Instantiate and return the named AI provider.

    Args:
        name: Provider name. Falls back to DEFAULT_AI_PROVIDER from config.

    Returns:
        An instance of the requested BaseAIProvider subclass.

    Raises:
        ValueError: If the provider name is not in the registry.
    """
    from config import DEFAULT_AI_PROVIDER
    name = name or DEFAULT_AI_PROVIDER
    if name not in REGISTRY:
        raise ValueError(
            f"Unknown provider '{name}'. Choose from: {list(REGISTRY)}"
        )
    return REGISTRY[name]()
