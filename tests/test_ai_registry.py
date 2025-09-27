from core.ai_registry import load_map, select_model

def test_select_model_defaults():
    m = load_map()
    p, model = select_model("strategy")
    assert isinstance(p, str) and isinstance(model, str)
    assert p == m["default"]["provider"]
    assert model == m["default"]["model"]

def test_select_model_per_role_overrides():
    # 'coding' role exists in the default fixture; should resolve cleanly
    p, model = select_model("coding")
    assert p and model
