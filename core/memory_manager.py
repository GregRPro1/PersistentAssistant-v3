# core/memory_manager.py — assemble compact context from memory summaries
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
import yaml, itertools

ROOT = Path(__file__).resolve().parents[1]
MEMDIR = ROOT / "memory"
RULES  = ROOT / "config" / "memory" / "include_rules.yaml"

def _load_rules():
    try:
        return yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    except Exception:
        return {"include_last_n_days": 7, "max_records": 12, "max_chars": 2000, "dedupe_by_source": True}

def _iter_summaries(days: int):
    if not MEMDIR.exists():
        return []
    files = sorted(MEMDIR.glob("summary_*.yaml"), reverse=True)
    if not days:
        return files
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    keep = []
    for f in files:
        stem = f.stem.replace("summary_","")
        try:
            dt = datetime.strptime(stem, "%Y%m%d").replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                keep.append(f)
        except Exception:
            keep.append(f)
    return keep

def build_context(max_snippets: int | None = None) -> str:
    rules = _load_rules()
    days   = int(rules.get("include_last_n_days", 7) or 7)
    maxrec = int(rules.get("max_records", 12) or 12)
    maxch  = int(rules.get("max_chars", 2000) or 2000)
    topics = rules.get("topics") or []

    # cap by caller
    if isinstance(max_snippets, int) and max_snippets > 0:
        maxrec = min(maxrec, max_snippets)

    lines=[]
    for f in _iter_summaries(days):
        try:
            items = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        except Exception:
            continue
        for rec in items:
            if topics and rec.get("topic") not in topics:
                continue
            ts = rec.get("timestamp","")
            tp = rec.get("topic","general")
            prm = (rec.get("prompt") or "")[:140]
            rep = (rec.get("reply") or "")[:160]
            lines.append(f"- [{ts}] {tp} :: {prm} -> {rep}")

    # de-dup
    seen=set()
    uniq=[]
    for ln in lines:
        if ln not in seen:
            seen.add(ln); uniq.append(ln)
    uniq = uniq[:maxrec]
    block = "\n".join(uniq)
    if len(block) > maxch:
        block = block[:maxch] + "\n... [memory truncated]"
    return block
