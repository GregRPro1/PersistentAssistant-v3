import pathlib, yaml, datetime
try:
    import pyperclip
except Exception:
    pyperclip = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
plan = ROOT / "project" / "plans" / "project_plan_v3.yaml"
packs = sorted((ROOT / "tmp" / "feedback").glob("pack_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
latest = str(packs[0].resolve()) if packs else "(none)"

cur = "(unknown)"; nxt = "(unknown)"
if plan.exists():
    with open(plan, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    cur = (d.get("meta",{}) or {}).get("current_step") or "(unknown)"
    # pick first planned/in_progress that isn't current
    for ph in d.get("phases",[]) or []:
        for st in ph.get("steps",[]) or []:
            if st.get("status") in ("planned","in_progress") and st.get("id") != cur:
                nxt = st.get("id"); break
        if nxt != "(unknown)": break

line = f"PLAN: {cur} -> next {nxt} | PACK: {latest}"
dest = ROOT / "tmp" / "phone" / "digest.txt"
dest.write_text(line, encoding="utf-8")
print(line)
if pyperclip:
    try: pyperclip.copy(line)
    except Exception: pass
