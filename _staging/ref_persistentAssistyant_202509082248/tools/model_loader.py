from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, yaml
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [
    ROOT / "config" / "model_catalog.yaml",
    ROOT / "config" / "ai_models.yaml",
    ROOT / "ai_models.yaml",
]

CAP_HINTS = {
    "chat":   ["gpt", "chat", "sonnet", "llama", "mixtral", "qwen", "claude"],
    "image":  ["vision", "image", "sd", "diffusion", " dall", "flux", "kandinsky"],
    "audio":  ["audio", "whisper", "tts", "asr", "speech"],
    # embeddings / tools / code fall back to "other"
}

def _infer_caps(model_id: str) -> list[str]:
    mid = (model_id or "").lower()
    caps = []
    for cap, keys in CAP_HINTS.items():
        if any(k in mid for k in keys):
            caps.append(cap)
    return caps or ["other"]

def _normalize_models(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected output:
    {
      providers: {
        openai: {
          models: {
            gpt-4o-mini: {
              capabilities: [...],
              input_cost_per_1k: float|None,
              output_cost_per_1k: float|None,
            }, ...
          }
        }, ...
      }
    }
    """
    providers = d.get("providers") or {}
    for p, pd in providers.items():
        models = pd.get("models") or {}
        for mid, meta in list(models.items()):
            caps = meta.get("capabilities") or _infer_caps(mid)
            meta["capabilities"] = caps
            # leave costs as-is if present
            models[mid] = meta
        pd["models"] = models
        providers[p] = pd
    return {"providers": providers}

def load_ai_models() -> Dict[str, Any]:
    for path in CANDIDATES:
        if path.exists():
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                return _normalize_models(raw)
            except Exception:
                continue
    return {"providers": {}}
