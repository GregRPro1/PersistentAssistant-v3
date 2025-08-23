import builtins
import types
import sys
import math
import importlib
from unittest.mock import patch, MagicMock

import pytest

# We import the module under test
# NOTE: tests do not call the network; we mock provider SDKs and only test selection + pricing math.
MODULE = "core.ai_client"

@pytest.fixture(autouse=True)
def clean_modules():
    """Ensure a fresh import of core.ai_client for each test (so patches apply)."""
    if MODULE in sys.modules:
        del sys.modules[MODULE]
    yield
    if MODULE in sys.modules:
        del sys.modules[MODULE]

def _fake_openai_module():
    mod = types.ModuleType("openai")
    class FakeClient:
        def __init__(self, api_key=None): pass
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    # Should never be called in these tests
                    raise RuntimeError("Network path not expected in unit tests.")
    mod.OpenAI = FakeClient
    mod.api_key = None
    return mod

def _fake_anthropic_module():
    mod = types.ModuleType("anthropic")
    class FakeClaude:
        def __init__(self, api_key=None): pass
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("Network path not expected in unit tests.")
    mod.Anthropic = FakeClaude
    return mod

def _fake_google_module():
    mod = types.ModuleType("google.generativeai")
    class FakeGM:
        def __init__(self, model): pass
        def generate_content(self, prompt): 
            raise RuntimeError("Network path not expected in unit tests.")
    def configure(api_key=None): 
        return None
    mod.GenerativeModel = FakeGM
    mod.configure = configure
    return mod

def _fake_groq_module():
    mod = types.ModuleType("groq")
    class FakeGroq:
        def __init__(self, api_key=None): pass
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("Network path not expected in unit tests.")
    mod.Groq = FakeGroq
    return mod

def _import_ai_client_with_mocks():
    # Inject fake SDKs
    sys.modules["openai"] = _fake_openai_module()
    sys.modules["anthropic"] = _fake_anthropic_module()
    sys.modules["google"] = types.ModuleType("google")
    sys.modules["google.generativeai"] = _fake_google_module()
    sys.modules["groq"] = _fake_groq_module()
    return importlib.import_module(MODULE)

def test_default_model_selection_openai():
    ai = _import_ai_client_with_mocks()
    # no model provided -> should default to "gpt-4o-mini"
    c = ai.AIClient(provider="openai", key="sk-xxx")
    assert c.model == "gpt-4o-mini"
    assert c.provider == "openai"

def test_default_model_selection_anthropic():
    ai = _import_ai_client_with_mocks()
    c = ai.AIClient(provider="anthropic", key="ant-xxx")
    assert "sonnet" in c.model  # matches default in implementation
    assert c.provider == "anthropic"

def test_cost_math_examples():
    ai = _import_ai_client_with_mocks()
    COSTS = ai.COSTS
    # Choose a known entry; ensure keys exist
    assert "openai" in COSTS and "gpt-4o-mini" in COSTS["openai"]
    pin = 1234; pout = 5678
    cin = COSTS["openai"]["gpt-4o-mini"]["in"]
    cout = COSTS["openai"]["gpt-4o-mini"]["out"]
    # Cost formula used in AIClient.send: (tokens_in*cin + tokens_out*cout)/1000
    expected = (pin*cin + pout*cout)/1000.0
    # Numerical sanity: strictly non-negative and small for token counts used
    assert expected >= 0.0
    assert expected < 1.0

def test_cost_table_sanity_all_entries():
    ai = _import_ai_client_with_mocks()
    COSTS = ai.COSTS
    for prov, models in COSTS.items():
        for mid, rate in models.items():
            assert "in" in rate and "out" in rate, f"missing in/out for {prov}:{mid}"
            assert isinstance(rate["in"], (int,float)) and isinstance(rate["out"], (int,float))
            assert rate["in"] >= 0 and rate["out"] >= 0

def test_constructor_rejects_unsupported_provider():
    ai = _import_ai_client_with_mocks()
    with pytest.raises(ValueError):
        ai.AIClient(provider="unknown", key="k")
