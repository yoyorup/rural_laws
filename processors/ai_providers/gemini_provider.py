"""Google Gemini AI provider."""

import logging
from typing import Optional

from processors.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 4096


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: Optional[str] = None):
        from config import GEMINI_API_KEY, GEMINI_MODEL
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL or "gemini-2.0-flash"
        self._client = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError:
                raise ImportError(
                    "google-generativeai package is required. "
                    "Run: pip install google-generativeai>=0.8.0"
                )
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Please add it to your .env file."
                )
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(
                model_name=self.model,
                generation_config={"max_output_tokens": _DEFAULT_MAX_TOKENS},
            )
        return self._client

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.client.generate_content(full_prompt)
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
        return ""
