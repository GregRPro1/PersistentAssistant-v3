# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, re, ast, yaml, sys
from datetime import datetime, timezone
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INV_PATH = os.path.join(ROOT, "data", "insights", "deep_inventory.yaml")
OUT_YAML = os.path.join(ROOT, "data", "insights", "reflection_report.yaml")
OUT_TXT  = os.path.join(ROOT, "tmp", "reflection_summary.txt")

GUI_CLASS_BASES = {"QMainWindow","QWidget","QDialog","QTabWidget","QDockWidget"}
BTN_CLASS = "QPushButton"

def load_inventory_paths():
    files = []
    if os.path.exists(INV_PATH):
        try:
            with open(INV_PATH,"r",encoding="utf-8") as f:
                inv = yaml.safe_load(f) or {}
            raw = inv.get("files", [])
            for item in raw:
                if isinstance(item, str):
                    files.append(item)
                elif isinstance(item, dict) and "path" in item:
                    files.append(item["path"])
        except Exception:
            pass
    return files

def glob_fs_paths():
    # fallback: walk filesystem for python files under gui/
    res = []
    gui_root = os.path.join(ROOT, "gui")
    for base, _, files in os.walk(gui_root):
        for fn in files:
            if fn.lower().endswith(".py"):
                rel = os.path.relpath(os.path.join(base, fn), ROOT).replace("\\","/")
                res.append(rel)
    return res

def read(path):
    try:
        with open(os.path.join(ROOT, path), "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def parse_gui_info(path, text):
    info = {
        "path": path,
        "classes": [],
        "buttons": [],
        "handlers": [],
        "connections": [],
        "notes": [],
    }
    try:
        tree = ast.parse(text)
    except Exception as e:
        info["notes"].append(f"AST parse failed: {e}")
        return info

    class_bases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = set()
            for b in node.bases:
                if hasattr(b, "id") and isinstance(b.id, str):
                    bases.add(b.id)
                elif hasattr(b, "attr") and isinstance(b.attr, str):
                    bases.add(b.attr)
            if bases & GUI_CLASS_BASES:
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                info["classes"].append({"name": node.name, "bases": sorted(bases), "methods": methods})

    for m in re.finditer(rf"{BTN_CLASS}\(\s*['\"]([^'\"]+)['\"]\s*\)", text):
        info["buttons"].append({"text": m.group(1)})

    for m in re.finditer(r"\.clicked\.connect\(([^)]+)\)", text):
        info["connections"].append(m.group(1).strip())

    if "def ensure_api_send_button" in text:
        info["handlers"].append("ensure_api_send_button")
    if "def on_send_api_clicked" in text:
        info["handlers"].append("on_send_api_clicked")

    return info

def main():
    inv_paths = load_inventory_paths()
    fs_paths  = glob_fs_paths()
    candidates = sorted(set([p.replace("\\","/") for p in inv_paths + fs_paths if p.lower().endswith(".py")]))
    gui_files = [p for p in candidates if p.startswith("gui/") or "PyQt6" in read(p)]

    results = []
    for p in gui_files:
        results.append(parse_gui_info(p, read(p)))

    checks = {
        "ChatTab_present": any("chat_tab.py" in r["path"] for r in results),
        "ensure_api_send_button_present": any("ensure_api_send_button" in r["handlers"] for r in results),
        "on_send_api_clicked_present": any("on_send_api_clicked" in r["handlers"] for r in results),
        "send_button_text_present": any(any(b.get("text")=="Send to AI (API)" for b in r["buttons"]) for r in results),
    }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gui_files_count": len(gui_files),
        "gui_files": gui_files[:],
        "details": results,
        "checks": checks
    }

    os.makedirs(os.path.dirname(OUT_YAML), exist_ok=True)
    with open(OUT_YAML,"w",encoding="utf-8") as f:
        yaml.safe_dump(summary, f, sort_keys=False)

    os.makedirs(os.path.dirname(OUT_TXT), exist_ok=True)
    lines = []
    lines.append("=== Reflection Summary ===")
    lines.append(f"GUI files: {len(gui_files)}")
    lines.append(f"ChatTab present: {checks['ChatTab_present']}")
    lines.append(f"ensure_api_send_button: {checks['ensure_api_send_button_present']}")
    lines.append(f"on_send_api_clicked: {checks['on_send_api_clicked_present']}")
    lines.append(f"Send button text found: {checks['send_button_text_present']}")
    lines.append("")
    lines.append("Key GUI files:")
    for p in gui_files[:20]:
        lines.append(f" - {p}")
    with open(OUT_TXT,"w",encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))

if __name__ == "__main__":
    main()
