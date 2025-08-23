import importlib, sys, json
from importlib import import_module

res = {"ok": False, "module": None, "init_ok": False, "error": None}
try:
    mw = import_module("gui.main_window")
    # after module import, PlanTrackerTab symbol should be bound
    # locate it by re-importing where the symbol is taken from
    from gui.tabs.plan_tracker_tab_compat import PlanTrackerTab as CompatPT
    res["module"] = CompatPT.__module__
    try:
        _ = CompatPT(plan_path=None)
        res["init_ok"] = True
    except Exception as e:
        res["error"] = f"init: {e.__class__.__name__}: {e}"
    res["ok"] = True
except Exception as e:
    res["error"] = f"import: {e.__class__.__name__}: {e}"

print(json.dumps(res, indent=2))
