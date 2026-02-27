"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Call the AI model and return raw text response."""

    def is_available(self) -> bool:
        """Return True if API key is configured."""
        return True
