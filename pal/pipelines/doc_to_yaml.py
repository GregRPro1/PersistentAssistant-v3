"""
Doc -> YAML converter pipeline using the provider-agnostic adapter.
"""
from pathlib import Path
from typing import Dict, Any
from pal.adapters.llm.base import Registry  # type: ignore

def doc_to_yaml(doc_path: Path, provider: str="openai") -> Dict[str, Any]:
    text = Path(doc_path).read_text(encoding="utf-8")
    adapter = Registry.get(provider)
    # VERY stub: wrap in YAML-like dict; real conversion would parse text.
    result = adapter.generate(f"Convert this document to PAL YAML tasks:\n{text[:200]}")
    return {"provider": provider, "result": result}
