from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import csv, os, sys, textwrap, yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[1]
INTERACTIONS_DIR = ROOT / "data" / "interactions"
CSV_PATH = ROOT / "logs" / "ai_request_log.csv"

def _ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _short(s: str, n: int = 320) -> str:
    if s is None: return ""
    s = str(s)
    return s if len(s) <= n else s[:n] + "…"

def log_interaction(prompt: str, result: Dict[str, Any], ui_source: str = "ChatTab") -> Path:
    INTERACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%d_%H%M%S")
    ypath = INTERACTIONS_DIR / f"INT_{stamp}.yaml"

    provider = result.get("provider")
    model = result.get("model")
    tokens_in = result.get("tokens_in")
    tokens_out = result.get("tokens_out")
    cost = result.get("cost")
    elapsed = result.get("time")
    reply = result.get("reply")

    record = {
        "timestamp": ts.isoformat().replace("+00:00","Z"),
        "ui_source": ui_source,
        "provider": provider,
        "model": model,
        "tokens_in": int(tokens_in) if isinstance(tokens_in, (int,float)) else tokens_in,
        "tokens_out": int(tokens_out) if isinstance(tokens_out, (int,float)) else tokens_out,
        "cost_usd": float(cost) if isinstance(cost,(int,float)) else cost,
        "elapsed_sec": float(elapsed) if isinstance(elapsed,(int,float)) else elapsed,
        "prompt_preview": _short(prompt, 512),
        "reply_preview": _short(reply, 1024),
    }
    with open(ypath, "w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, sort_keys=False)

    headers = ["timestamp","ui_source","provider","model","tokens_in","tokens_out","cost_usd","elapsed_sec"]
    csv_exists = CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        if not csv_exists: w.writeheader()
        w.writerow({k: record.get(k,"") for k in headers})

    return ypath

def log_error(prompt: str, provider: str, model: str, summary: str, detail: str, meta: Dict[str, Any], ui_source: str = "ChatTab") -> Path:
    """
    Records an error interaction separately: data/interactions/ERR_*.yaml
    """
    INTERACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%d_%H%M%S")
    ypath = INTERACTIONS_DIR / f"ERR_{stamp}.yaml"
    errrec = {
        "timestamp": ts.isoformat().replace("+00:00","Z"),
        "ui_source": ui_source,
        "provider": provider,
        "model": model,
        "summary": _short(summary, 200),
        "detail": _short(detail, 4000),
        "meta": meta or {},
        "prompt_preview": _short(prompt, 512),
    }
    with open(ypath, "w", encoding="utf-8") as f:
        yaml.safe_dump(errrec, f, sort_keys=False)
    return ypath
