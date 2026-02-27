"""Anthropic Claude AI provider."""

import logging
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS
from processors.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseAIProvider):
    name = "claude"

    def __init__(self, api_key: str = ANTHROPIC_API_KEY, model: str = CLAUDE_MODEL):
        self.api_key = api_key
        self.model = model
        self._client: Optional[anthropic.Anthropic] = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set. Please add it to your .env file."
                )
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text if message.content else ""
        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API connection error: {e}")
        except anthropic.RateLimitError as e:
            logger.error(f"Claude API rate limit: {e}")
        except anthropic.APIStatusError as e:
            logger.error(f"Claude API status error {e.status_code}: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}")
        return ""
