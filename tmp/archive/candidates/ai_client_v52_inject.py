# core/ai_client.py — memory-injecting candidate
import os, sys, time, logging
from typing import Dict, Any

# lazy SDK imports (allow tests without SDKs)
try: import openai
except Exception: openai=None
try: import anthropic
except Exception: anthropic=None
try: import google.generativeai as genai
except Exception: genai=None
try: import groq
except Exception: groq=None

import yaml
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COSTS = {
    "openai": {"gpt-4o-mini": {"in": 0.00000015, "out": 0.0000006}},
    "anthropic": {"claude-3-5-sonnet-20240620": {"in": 0.000003, "out": 0.000015}},
    "groq": {
        "llama-3.1-8b-instant": {"in": 0.00000005, "out": 0.00000008},
        "llama-3.1-70b-versatile": {"in": 0.0000006, "out": 0.0000008},
    },
    "google": {"gemini-1.5-pro-latest": {"in": 0.00000035, "out": 0.00000105}},
    "deepseek": {"deepseek-chat": {"in": 0.00000014, "out": 0.00000028}},
}

DEFAULT_MODEL = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20240620",
    "groq": "llama-3.1-8b-instant",
    "google": "gemini-1.5-pro-latest",
    "deepseek": "deepseek-chat",
}

ROOT = Path(__file__).resolve().parents[1]
PROJ_CFG = ROOT / "config" / "projects" / "persistent_assistant_v3.yaml"

def _load_project_cfg():
    try:
        return yaml.safe_load(PROJ_CFG.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _memory_enabled_and_limit():
    cfg = _load_project_cfg()
    mi = cfg.get("memory_injection") or {}
    return bool(mi.get("enabled", False)), int(mi.get("max_snippets", 5) or 5)

def _maybe_build_memory(max_snips: int) -> str:
    try:
        from core.memory_manager import build_context
        return build_context(max_snippets=max_snips)
    except Exception as e:
        logging.warning("memory_manager unavailable: %s", e)
        return ""

class AIClient:
    def __init__(self, provider: str, key: str, model: str | None = None):
        if not provider:
            raise ValueError("Provider must be specified")
        provider = provider.lower()
        if provider not in DEFAULT_MODEL:
            raise ValueError(f"Unsupported provider: {provider}")
        self.provider = provider
        self.model = model or DEFAULT_MODEL[provider]
        self.key = key
        self.client = None

        if provider == "openai":
            if openai:
                openai.api_key = key
                self.client = openai.OpenAI(api_key=key)
        elif provider == "anthropic":
            if anthropic:
                self.client = anthropic.Anthropic(api_key=key)
        elif provider == "groq":
            if groq:
                self.client = groq.Groq(api_key=key)
        elif provider == "google":
            if genai:
                genai.configure(api_key=key)
                self.client = genai.GenerativeModel(self.model)
        elif provider == "deepseek":
            # not wired
            self.client = None

    def send(self, prompt: str, *, include_memory: bool | None = None) -> Dict[str, Any]:
        """
        Optionally prepend memory context before sending.
        include_memory: None -> read from project config; True/False overrides.
        """
        mem_on, mem_limit = _memory_enabled_and_limit()
        use_mem = mem_on if include_memory is None else bool(include_memory)
        context_used = False
        final_prompt = prompt

        if use_mem:
            ctx = _maybe_build_memory(mem_limit)
            if ctx.strip():
                final_prompt = f"=== Context (latest) ===\n{ctx}\n\n=== Prompt ===\n{prompt}"
                context_used = True

        start = time.time()
        reply = None
        tokens_in = tokens_out = 0

        if self.provider == "openai" and self.client:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"user","content": final_prompt}],
            )
            reply = resp.choices[0].message.content
            tokens_in = getattr(resp.usage,"prompt_tokens",0)
            tokens_out = getattr(resp.usage,"completion_tokens",0)
        elif self.provider == "anthropic" and self.client:
            resp = self.client.messages.create(
                model=self.model, max_tokens=512,
                messages=[{"role":"user","content": final_prompt}],
            )
            reply = resp.content[0].text if getattr(resp,"content",None) else ""
            tokens_in = getattr(resp.usage,"input_tokens",0)
            tokens_out = getattr(resp.usage,"output_tokens",0)
        elif self.provider == "groq" and self.client:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"user","content": final_prompt}],
            )
            reply = resp.choices[0].message.content
            tokens_in = getattr(resp.usage,"prompt_tokens",0)
            tokens_out = getattr(resp.usage,"completion_tokens",0)
        elif self.provider == "google" and self.client:
            resp = self.client.generate_content(final_prompt)
            reply = getattr(resp,"text","")
            tokens_in = int(len(final_prompt.split())*1.3)
            tokens_out = int(len((reply or "").split())*1.3)
        else:
            reply = "(no client bound for provider)"

        elapsed = time.time() - start
        rates = COSTS.get(self.provider, {}).get(self.model, {"in":0.0,"out":0.0})
        cost = (tokens_in*rates["in"] + tokens_out*rates["out"]) / 1000.0

        logging.info("[MEM INJECT] used=%s, limit=%d", context_used, mem_limit)

        return {
            "reply": reply,
            "provider": self.provider,
            "model": self.model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
            "time": elapsed,
            "context_used": context_used,
        }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python core/ai_client.py '<prompt>' <provider>")
        sys.exit(1)
    prompt = sys.argv[1]
    provider = sys.argv[2].lower()
    # Load key from env or YAML (OpenAI path only for demo)
    key = os.getenv("OPENAI_API_KEY") if provider=="openai" else None
    if not key:
        try:
            with open("C:/Secure/api_keys/keys.yaml","r",encoding="utf-8") as f:
                keys = yaml.safe_load(f) or {}
            key = (((keys.get("keys") or {}).get("default") or {}).get(provider) or {}).get("paid")
        except Exception:
            pass
    if not key:
        print(f"No API key found for {provider}")
        sys.exit(1)
    client = AIClient(provider=provider, key=key)
    print(client.send(prompt))
