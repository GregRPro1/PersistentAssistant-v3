# core/prompt_formatter.py (v5.2 candidate) — memory-aware prompt wrapper
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
import yaml

ROOT = Path(__file__).resolve().parents[1]
MEMDIR = ROOT / "memory"
RULES  = ROOT / "config" / "memory" / "include_rules.yaml"

def _load_rules():
    try:
        return yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _iter_summaries(from_days: int):
    if not MEMDIR.exists(): return []
    files = sorted(MEMDIR.glob("summary_*.yaml"), reverse=True)
    if from_days is None: 
        return files
    cutoff = datetime.now(timezone.utc) - timedelta(days=from_days)
    keeps = []
    for f in files:
        # parse YYYYMMDD
        name = f.stem.replace("summary_","")
        try:
            dt = datetime.strptime(name, "%Y%m%d").replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                keeps.append(f)
        except Exception:
            keeps.append(f)
    return keeps

def _build_memory_block(rules: dict) -> str:
    days   = int(rules.get("include_last_n_days", 7) or 7)
    maxrec = int(rules.get("max_records", 12) or 12)
    maxch  = int(rules.get("max_chars", 2000) or 2000)
    topics = rules.get("topics") or []
    header = (rules.get("prepend_header") or "").strip()

    acc = []
    for f in _iter_summaries(days):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        except Exception:
            continue
        for rec in data:
            if topics and rec.get("topic") not in topics:
                continue
            acc.append(f"- [{rec.get('timestamp')}] {rec.get('topic','general')} :: {rec.get('prompt','')[:120]} -> {rec.get('reply','')[:160]}")

    # de-dupe if requested
    if bool(rules.get("dedupe_by_source", True)):
        # stable order; drop exact duplicate strings
        seen=set(); uniq=[]
        for line in acc:
            if line not in seen:
                seen.add(line); uniq.append(line)
        acc = uniq

    # limit records
    acc = acc[:maxrec]
    block = "\n".join(acc)
    if len(block) > maxch:
        block = block[:maxch] + "\n... [memory truncated]"
    return (header + "\n" + block).strip() if header else block

def format_prompt(
    user_input: str,
    system: str | None = None,
    include_memory: bool = False
) -> str:
    """
    Returns a single string payload suitable for a single-message send.
    - When include_memory=True, prepends a compact memory block built from memory/summary_*.yaml
    - Keeps BC for existing callers (system can be None).
    """
    parts = []
    if system:
        parts.append(f"[SYSTEM]\n{system}\n")
    if include_memory:
        rules = _load_rules()
        mem = _build_memory_block(rules)
        if mem:
            parts.append(mem + "\n")
    parts.append("[USER]\n" + (user_input or "").strip())
    return "\n\n".join(parts).strip()
