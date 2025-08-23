import json
ok = True; err = None
try:
    from gui.tabs.plan_tree_tab import PlanTreeTab
    t = PlanTreeTab()
except Exception as e:
    ok = False; err = f"{e.__class__.__name__}: {e}"
print(json.dumps({"ok": ok, "error": err}, indent=2))
