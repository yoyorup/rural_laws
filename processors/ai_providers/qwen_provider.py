"""Alibaba Qwen (DashScope OpenAI-compatible) AI provider."""

from typing import Optional

from processors.ai_providers.openai_provider import OpenAIProvider


class QwenProvider(OpenAIProvider):
    name = "qwen"
    _default_model = "qwen-max"
    _base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, api_key: str = "", model: Optional[str] = None):
        from config import QWEN_API_KEY, QWEN_MODEL
        super().__init__(
            api_key=api_key or QWEN_API_KEY,
            model=model or QWEN_MODEL or self._default_model,
            base_url=self._base_url,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
