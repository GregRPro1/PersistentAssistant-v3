import os, re, sys, shutil, string, argparse
from pathlib import Path

try:
    import yaml
except Exception:
    print("PyYAML missing. Run: pip install pyyaml", file=sys.stderr); raise

THIS = Path(__file__).resolve()

def find_repo_root(start: Path) -> Path:
    p = start
    for _ in range(8):
        if (p / ".git").exists() or (p / "project" / "plans").exists():
            return p
        p = p.parent
    # fallback: three levels up from tools\py\plan\normalize_plan_yaml.py -> repo root
    return THIS.parents[3]

def first_sentence(s: str) -> str:
    s = (s or "").strip()
    if not s: return ""
    return re.split(r"[.!?\n]", s, 1)[0].strip()

def natkey(step_id: str):
    parts = str(step_id).split(".")
    out = []
    for p in parts:
        out.append((0, int(p)) if p.isdigit() else (1, p.lower()))
    return out

def normalize_step(step):
    sid = str(step.get("id", "")).strip()
    if not sid: raise ValueError("Step without id")

    base = {"id": sid, "status": str(step.get("status", "planned"))}

    title = (step.get("title") or "").strip()
    desc  = (step.get("description") or step.get("desc") or "").strip()
    if not title:
        fs = first_sentence(desc)
        title = fs or sid
    if title: base["title"] = title
    if desc:  base["description"] = desc

    for k in ("files", "tags", "success", "owner"):
        if k in step: base[k] = step[k]

    substeps = []
    items = step.get("items") or []
    if isinstance(items, list) and items:
        letters = iter(string.ascii_lowercase)
        for it in items:
            letter = next(letters)
            cid = f"{sid}.{letter}"
            if isinstance(it, dict):
                st  = str(it.get("status") or "planned")
                ttl = (it.get("title") or "").strip() or cid
                dsc = (it.get("description") or it.get("desc") or "").strip()
            else:
                st, ttl, dsc = "planned", str(it), ""
            ss = {"id": cid, "status": st, "title": ttl}
            if dsc: ss["description"] = dsc
            substeps.append(ss)

    return base, substeps

def normalize(data: dict) -> dict:
    if not isinstance(data, dict) or "phases" not in data:
        raise SystemExit("Plan YAML missing top-level 'phases'. (Schema unchanged.)")

    for ph in data["phases"]:
        steps = ph.get("steps") or []
        new_steps = []
        for st in steps:
            base, subs = normalize_step(st)
            new_steps.append(base)
            new_steps.extend(subs)
        new_steps.sort(key=lambda s: natkey(s.get("id", "")))
        ph["steps"] = new_steps
    return data

def main():
    ap = argparse.ArgumentParser(description="Normalize project_plan_v3.yaml in place (schema preserved).")
    ap.add_argument("--plan", default=None, help="Path to project_plan_v3.yaml (default: project\\plans\\project_plan_v3.yaml under repo root)")
    ap.add_argument("--inplace", action="store_true", help="Overwrite source after writing a .bak")
    args = ap.parse_args()

    repo = find_repo_root(THIS.parent)
    plan_path = Path(args.plan) if args.plan else (repo / r"project\plans\project_plan_v3.yaml")
    plan_path = plan_path.resolve()

    if not plan_path.exists():
        print(f"Plan not found: {plan_path}", file=sys.stderr)
        raise SystemExit(2)

    backup = plan_path.with_suffix(".bak")
    out_norm = plan_path.with_suffix(".normalized.yaml")

    with plan_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    norm = normalize(data)

    with out_norm.open("w", encoding="utf-8") as f:
        yaml.safe_dump(norm, f, allow_unicode=True, sort_keys=False, width=100)
    print(f"[OK] Wrote normalized preview: {out_norm}")

    if args.inplace:
        if not backup.exists():
            shutil.copyfile(plan_path, backup)
            print(f"[OK] Backup: {backup}")
        shutil.copyfile(out_norm, plan_path)
        print(f"[OK] Updated in place: {plan_path}")

if __name__ == "__main__":
    main()
