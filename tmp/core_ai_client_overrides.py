# core/ai_client.py
# G. Rapson, GR-Analysis - 2025-08-18  (Enhanced: pricing overrides bridge)

import os
import sys
import time
import logging
import yaml
import openai
import anthropic
import google.generativeai as genai
import groq
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -------------------------------
# Cost tables ($ per 1K tokens)
# -------------------------------
COSTS = {
    "openai": {
        "gpt-4o-mini": {"in": 0.00000015, "out": 0.0000006},  # $0.15 / $0.60 per 1M tokens
    },
    "anthropic": {
        "claude-3-5-sonnet-20240620": {"in": 0.000003, "out": 0.000015},  # $3 / $15 per 1M tokens
    },
    "groq": {
        "llama-3.1-8b-instant": {"in": 0.00000005, "out": 0.00000008},  # example pricing
        "llama-3.1-70b-versatile": {"in": 0.0000006, "out": 0.0000008},
    },
    "google": {
        "gemini-1.5-pro-latest": {"in": 0.00000035, "out": 0.00000105},  # $0.35 / $1.05 per 1M tokens
    },
    "deepseek": {
        "deepseek-chat": {"in": 0.00000014, "out": 0.00000028},
    }
}

# --- Pricing overrides bridge -----------------------------------------------
_OVERRIDES_PATH = os.path.join("config", "provider_pricing_overrides.yaml")

def _normalize_model(provider: str, model: str) -> str:
    """Map common aliases from overrides to canonical keys in COSTS."""
    alias = {
        "anthropic": {
            "claude-3.5-sonnet": "claude-3-5-sonnet-20240620",
        },
        "groq": {
            # example alias mapping if needed:
            "mixtral-8x7b": "mixtral-8x7b"  # only applies if present in COSTS
        },
        "openai": {},
        "google": {},
        "deepseek": {},
    }
    return alias.get(provider, {}).get(model, model)

def _load_pricing_overrides(path: str = _OVERRIDES_PATH) -> Dict[str, Dict[str, Dict[str, float]]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            logging.warning("Overrides file not a dict; ignoring.")
            return {}
        return data
    except Exception as e:
        logging.warning("Failed to load pricing overrides: %s", e)
        return {}

def _apply_overrides_to_costs():
    """Apply overrides to COSTS in-place. Supports keys:
       - input_cost_per_1k / output_cost_per_1k
       - in / out (direct)
    """
    overrides = _load_pricing_overrides()
    if not overrides:
        return
    applied = 0
    skipped = []
    for provider, models in overrides.items():
        if provider not in COSTS:
            skipped.append((provider, "*", "provider_not_found"))
            continue
        for model_name, vals in (models or {}).items():
            canon = _normalize_model(provider, model_name)
            if canon not in COSTS[provider]:
                skipped.append((provider, canon, "model_not_found"))
                continue
            if not isinstance(vals, dict):
                skipped.append((provider, canon, "bad_values"))
                continue
            # map synonyms
            in_key = "in"
            out_key = "out"
            if "input_cost_per_1k" in vals and vals["input_cost_per_1k"] is not None:
                COSTS[provider][canon][in_key] = float(vals["input_cost_per_1k"])
                applied += 1
            if "output_cost_per_1k" in vals and vals["output_cost_per_1k"] is not None:
                COSTS[provider][canon][out_key] = float(vals["output_cost_per_1k"])
                applied += 1
            # allow direct 'in'/'out' too
            if "in" in vals and vals["in"] is not None:
                COSTS[provider][canon]["in"] = float(vals["in"]); applied += 1
            if "out" in vals and vals["out"] is not None:
                COSTS[provider][canon]["out"] = float(vals["out"]); applied += 1
    if applied:
        logging.info("Applied %d pricing override entries.", applied)
    if skipped:
        for tup in skipped[:10]:
            logging.info("Override skipped: %s", tup)
        if len(skipped) > 10:
            logging.info("... %d more skipped", len(skipped) - 10)

# Apply overrides at import time (so AIClient sees updated COSTS)
_apply_overrides_to_costs()
# --- end bridge --------------------------------------------------------------

class AIClient:
    def __init__(self, provider: str = "openai", key: str = None, model: str = None):
        self.provider = provider
        self.key = key
        self.model = model
        self.client = None

        if provider == "openai":
            if key:
                openai.api_key = key
            if not model:
                self.model = "gpt-4o-mini"
            self.client = openai.OpenAI(api_key=key) if key else openai.OpenAI()

        elif provider == "anthropic":
            if not model:
                self.model = "claude-3-5-sonnet-20240620"
            self.client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()

        elif provider == "groq":
            if not model:
                self.model = "llama-3.1-8b-instant"
            self.client = groq.Groq(api_key=key) if key else groq.Groq()

        elif provider == "google":
            if not model:
                self.model = "gemini-1.5-pro-latest"
            if key:
                genai.configure(api_key=key)
            self.client = genai.GenerativeModel(self.model)

        elif provider == "deepseek":
            if not model:
                self.model = "deepseek-chat"
            raise NotImplementedError("DeepSeek client not wired yet")

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def send(self, prompt: str) -> Dict[str, Any]:
        """Send a prompt to the AI provider and return reply + cost info"""
        start = time.time()
        reply = None
        tokens_in, tokens_out = 0, 0

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            reply = response.choices[0].message.content
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            reply = response.content[0].text
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens

        elif self.provider == "groq":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            reply = response.choices[0].message.content
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

        elif self.provider == "google":
            response = self.client.generate_content(prompt)
            reply = response.text
            tokens_in = int(len(prompt.split()) * 1.3)
            tokens_out = int(len(reply.split()) * 1.3)

        else:
            raise ValueError(f"Provider {self.provider} not supported in send()")

        elapsed = time.time() - start

        # Compute cost with possibly overridden COSTS
        c = COSTS.get(self.provider, {}).get(self.model, {"in": 0, "out": 0})
        cost = (tokens_in * c["in"] + tokens_out * c["out"]) / 1000

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
    # Keep your existing key-loading behavior, but don’t hard-fail if absent
    keys_path = "C:/Secure/api_keys/keys.yaml"
    key = None
    if os.path.exists(keys_path):
        with open(keys_path, "r") as f:
            keys = yaml.safe_load(f) or {}
        key = ((keys.get("keys") or {}).get("default") or {}).get(provider, {}).get("paid")

    client = AIClient(provider=provider, key=key)
    res = client.send(prompt)
    print(res)
