"""OpenAI-compatible AI provider (also base for Qwen and GLM)."""

import logging
from typing import Optional

from processors.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 4096


class OpenAIProvider(BaseAIProvider):
    name = "openai"
    _default_model = "gpt-4o"
    _base_url: Optional[str] = None

    def __init__(self, api_key: str = "", model: Optional[str] = None, base_url: Optional[str] = None):
        from config import OPENAI_API_KEY, OPENAI_MODEL
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL or self._default_model
        self.base_url = base_url or self._base_url
        self._client = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai package is required. Run: pip install openai>=1.0.0")
            if not self.api_key:
                raise ValueError(
                    f"{self.name.upper()}_API_KEY is not set. Please add it to your .env file."
                )
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=_DEFAULT_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI-compatible API error ({self.name}): {e}")
        return ""
