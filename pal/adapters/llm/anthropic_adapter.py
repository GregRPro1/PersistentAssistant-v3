"""
Anthropic/Claude adapter (stub).
"""
from .base import LLMAdapter, Registry

class ClaudeAdapter(LLMAdapter):
    name = "claude"

    def generate(self, prompt: str, **kwargs) -> str:
        return f"[claude-stub] {prompt[:60]}"

Registry.register(ClaudeAdapter())
