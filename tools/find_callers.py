# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import sys, yaml
if len(sys.argv)<2:
    print("usage: find_callers.py <symbol_name>")
    sys.exit(2)
sym = sys.argv[1]
d = yaml.safe_load(open("data/insights/deep_calls.yaml","r",encoding="utf-8"))
hits = [e for e in d.get("edges",[]) if e.get("symbol")==sym]
if not hits:
    print(f"[NO CALLERS] {sym}")
else:
    print(f"[CALLERS] {sym}")
    for e in hits:
        print(f"  {e['from_file']}  ->  {e['to_file']}  ({e['expr']})")
