"""
Backward-compatibility shim.

The original ClaudeProcessor is re-exported from law_processor so that any
existing code that imports it continues to work unchanged.
"""

from processors.ai_providers.claude_provider import ClaudeProvider
from processors.law_processor import LawProcessor


class ClaudeProcessor(LawProcessor):
    """Drop-in replacement for the original ClaudeProcessor.

    Accepts the same ``api_key`` keyword argument and internally creates a
    ClaudeProvider, then delegates all logic to LawProcessor.
    """

    def __init__(self, api_key: str = ""):
        from config import ANTHROPIC_API_KEY
        provider = ClaudeProvider(api_key=api_key or ANTHROPIC_API_KEY)
        if not provider.is_available():
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Please add it to your .env file."
            )
        super().__init__(provider)


__all__ = ["ClaudeProcessor"]
