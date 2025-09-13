from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def apply_proposal(proposal_path: str, apply: bool = False, repo_root: Optional[str] = None) -> Dict[str, Any]:
    root = Path(repo_root or ".").resolve()
    data = json.loads(Path(proposal_path).read_text(encoding="utf-8"))
    patches: List[Dict[str, Any]] = data.get("patches", [])
    results: List[Dict[str, Any]] = []
    all_ok = True
    for ph in patches:
        action = str(ph.get("action", "modify")).lower()
        tgt = Path(root / ph["path"]).resolve() if "path" in ph else None
        res: Dict[str, Any] = {"action": action, "path": ph.get("path")}
        try:
            if action == "add":
                content = ph.get("content", "")
                res["note"] = "add file"
                if apply:
                    assert tgt is not None
                    _ensure_parent(tgt); tgt.write_text(content, encoding="utf-8")
                res["ok"] = True
            elif action == "modify":
                content = ph.get("content", None)
                if content is None:
                    res["note"] = "no content -> skip modify"; res["ok"] = True
                else:
                    res["note"] = "overwrite file"
                    if apply:
                        assert tgt is not None
                        _ensure_parent(tgt); tgt.write_text(content, encoding="utf-8")
                    res["ok"] = True
            elif action == "delete":
                res["note"] = "delete file if exists"
                if apply and tgt and tgt.exists(): tgt.unlink()
                res["ok"] = True
            elif action == "rename":
                src = Path(root / ph["from_path"]).resolve() if ph.get("from_path") else None
                assert tgt is not None and src is not None
                res["from_path"] = ph.get("from_path"); res["note"] = "rename/move file"
                if apply:
                    _ensure_parent(tgt)
                    if src.exists(): shutil.move(str(src), str(tgt))
                res["ok"] = True
            else:
                res["ok"] = False; res["note"] = f"unknown action: {action}"
        except Exception as e:
            res["ok"] = False; res["error"] = repr(e)
        results.append(res); all_ok = all_ok and bool(res.get("ok"))
    return {"ok": all_ok, "dry_run": (not apply), "results": results}

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="patch_apply", allow_abbrev=False)
    p.add_argument("--proposal", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--root", type=str, default=".")
    return p

def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    out = apply_proposal(args.proposal, apply=bool(args.apply), repo_root=args.root)
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
