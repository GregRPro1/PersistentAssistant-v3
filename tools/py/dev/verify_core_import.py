import json, importlib
try:
    m = importlib.import_module("core.ai_client")
    print(json.dumps({"imported": True, "module": getattr(m, "__file__", None)}))
except Exception as e:
    print(json.dumps({"imported": False, "error": f"{type(e).__name__}: {e}"}))
