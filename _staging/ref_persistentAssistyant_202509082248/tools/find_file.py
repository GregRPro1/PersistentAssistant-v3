# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, sys, yaml, glob

INV = "data/insights/deep_inventory.yaml"

def main():
    target_name = sys.argv[1] if len(sys.argv)>1 else ""
    if not target_name:
        print("[ERR] target file name required"); sys.exit(2)

    candidates = []
    if os.path.exists(INV):
        try:
            with open(INV,"r",encoding="utf-8") as f:
                inv = yaml.safe_load(f) or {}
            for item in inv.get("files", []):
                if isinstance(item, str) and item.endswith(target_name):
                    candidates.append(item)
                elif isinstance(item, dict) and item.get("path","").endswith(target_name):
                    candidates.append(item["path"])
        except Exception:
            pass

    # Fallback: glob search
    if not candidates:
        for p in glob.glob("**/" + target_name, recursive=True):
            candidates.append(p.replace("\\","/"))

    if not candidates:
        print("[ERR] not found")
        sys.exit(3)

    # Prefer core/… path if present
    candidates.sort(key=lambda p: (0 if p.replace("\\","/").startswith("core/") else 1, p))
    print(candidates[0])
    sys.exit(0)

if __name__ == "__main__":
    main()
