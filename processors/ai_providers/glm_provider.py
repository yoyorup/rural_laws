"""Zhipu ChatGLM (OpenAI-compatible) AI provider."""

from typing import Optional

from processors.ai_providers.openai_provider import OpenAIProvider


class GLMProvider(OpenAIProvider):
    name = "glm"
    _default_model = "glm-4"
    _base_url = "https://open.bigmodel.cn/api/paas/v4/"

    def __init__(self, api_key: str = "", model: Optional[str] = None):
        from config import GLM_API_KEY, GLM_MODEL
        super().__init__(
            api_key=api_key or GLM_API_KEY,
            model=model or GLM_MODEL or self._default_model,
            base_url=self._base_url,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
