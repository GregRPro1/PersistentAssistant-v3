"""
Provider-agnostic LLM adapter interface for PAL.
All providers must implement: generate(prompt: str, **kwargs) -> str
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

class LLMAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        ...

class Registry:
    _providers: Dict[str, LLMAdapter] = {}

    @classmethod
    def register(cls, provider: LLMAdapter):
        cls._providers[provider.name] = provider

    @classmethod
    def get(cls, name: str) -> LLMAdapter:
        if name not in cls._providers:
            raise KeyError(f"LLM provider not registered: {name}")
        return cls._providers[name]
