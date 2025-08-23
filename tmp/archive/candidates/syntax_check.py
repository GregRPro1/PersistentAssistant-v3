from importlib.machinery import SourceFileLoader
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
def check(p):
    try:
        SourceFileLoader("x", str(p)).load_module()
        print("[CHECK OK]", p)
    except Exception as e:
        print("[CHECK FAIL]", p, "-", e)
for rel in ("tools/run_with_capture.py","tools/export_insights.py","tools/apply_and_pack.py"):
    check(ROOT/rel)
