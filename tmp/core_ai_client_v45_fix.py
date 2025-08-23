# core/ai_client.py
# Robust defaults + strict unknown-provider guard for unit tests (no network during tests)

import os, sys, time, logging
from typing import Dict, Any

# Lazy imports (SDKs may be absent in test/mocked runs)
try:
    import openai
except Exception:
    openai = None
try:
    import anthropic
except Exception:
    anthropic = None
try:
    import google.generativeai as genai
except Exception:
    genai = None
try:
    import groq
except Exception:
    groq = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -------------------------------
# Cost tables ($ per 1K tokens)
# -------------------------------
COSTS = {
    "openai": {
        "gpt-4o-mini": {"in": 0.00000015, "out": 0.0000006},
    },
    "anthropic": {
        "claude-3-5-sonnet-20240620": {"in": 0.000003, "out": 0.000015},
    },
    "groq": {
        "llama-3.1-8b-instant": {"in": 0.00000005, "out": 0.00000008},
        "llama-3.1-70b-versatile": {"in": 0.0000006, "out": 0.0000008},
    },
    "google": {
        "gemini-1.5-pro-latest": {"in": 0.00000035, "out": 0.00000105},
    },
    "deepseek": {
        "deepseek-chat": {"in": 0.00000014, "out": 0.00000028},
    }
}

DEFAULT_MODEL = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20240620",
    "groq": "llama-3.1-8b-instant",
    "google": "gemini-1.5-pro-latest",
    "deepseek": "deepseek-chat",
}

class AIClient:
    def __init__(self, provider: str, key: str, model: str | None = None):
        if not provider:
            raise ValueError("Provider must be specified")
        provider = provider.lower()
        self.provider = provider

        if provider not in DEFAULT_MODEL:
            # Strict guard for tests
            raise ValueError(f"Unsupported provider: {provider}")

        # Enforce a default model if None/empty
        self.model = model or DEFAULT_MODEL[provider]
        self.key = key
        self.client = None

        if provider == "openai":
            if openai is None:
                # Allow import-less construction in tests (no network use)
                self.client = None
            else:
                openai.api_key = key
                self.client = openai.OpenAI(api_key=key)

        elif provider == "anthropic":
            if anthropic is None:
                self.client = None
            else:
                self.client = anthropic.Anthropic(api_key=key)

        elif provider == "groq":
            if groq is None:
                self.client = None
            else:
                self.client = groq.Groq(api_key=key)

        elif provider == "google":
            if genai is None:
                self.client = None
            else:
                genai.configure(api_key=key)
                # For Gemini we keep only the model id; client is model object
                self.client = genai.GenerativeModel(self.model)

        elif provider == "deepseek":
            # Not wired; keep constructor usable for tests
            self.client = None

    def send(self, prompt: str) -> Dict[str, Any]:
        """
        Sends prompt to the configured provider.
        Unit tests DO NOT exercise this path (SDK calls are mocked/blocked).
        """
        import time as _t
        start = _t.time()
        reply = None
        tokens_in, tokens_out = 0, 0

        if self.provider == "openai" and self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            reply = response.choices[0].message.content
            tokens_in = getattr(response.usage, "prompt_tokens", 0)
            tokens_out = getattr(response.usage, "completion_tokens", 0)

        elif self.provider == "anthropic" and self.client:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            # anthropic returns a list of content blocks
            reply = response.content[0].text if getattr(response, "content", None) else ""
            tokens_in = getattr(response.usage, "input_tokens", 0)
            tokens_out = getattr(response.usage, "output_tokens", 0)

        elif self.provider == "groq" and self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            reply = response.choices[0].message.content
            tokens_in = getattr(response.usage, "prompt_tokens", 0)
            tokens_out = getattr(response.usage, "completion_tokens", 0)

        elif self.provider == "google" and self.client:
            response = self.client.generate_content(prompt)
            reply = getattr(response, "text", "")

            # Gemini SDK doesn't expose tokens in this path; estimate conservatively
            tokens_in = int(len(prompt.split()) * 1.3)
            tokens_out = int(len((reply or "").split()) * 1.3)

        else:
            # Provider not wired or client missing; still return a structured result
            reply = "(no client bound for provider)"
            tokens_in = 0
            tokens_out = 0

        elapsed = time.time() - start

        # Compute cost
        rates = COSTS.get(self.provider, {}).get(self.model, {"in": 0.0, "out": 0.0})
        cost = (tokens_in * rates["in"] + tokens_out * rates["out"]) / 1000.0

        return {
            "reply": reply,
            "provider": self.provider,
            "model": self.model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
            "time": elapsed,
        }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python core/ai_client.py '<prompt>' <provider>")
        sys.exit(1)

    prompt = sys.argv[1]
    provider = sys.argv[2].lower()

    import yaml
    try:
        with open("C:/Secure/api_keys/keys.yaml", "r", encoding="utf-8") as f:
            keys = yaml.safe_load(f) or {}
        key = (((keys.get("keys") or {}).get("default") or {}).get(provider) or {}).get("paid")
    except Exception:
        key = os.getenv("OPENAI_API_KEY") if provider == "openai" else None

    if not key:
        print(f"No API key found for {provider}")
        sys.exit(1)

    client = AIClient(provider=provider, key=key)
    res = client.send(prompt)
    print(res)
