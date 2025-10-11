"""
OpenAI adapter (stub). Reads key from OPENAI_API_KEY. This is a placeholder
for real integration; smoke tests import without calling external services.
"""
import os
from .base import LLMAdapter, Registry

class OpenAIAdapter(LLMAdapter):
    name = "openai"

    def generate(self, prompt: str, **kwargs) -> str:
        # Stub: do not call network in smoke. Return deterministic echo.
        return f"[openai-stub] {prompt[:60]}"

Registry.register(OpenAIAdapter())
