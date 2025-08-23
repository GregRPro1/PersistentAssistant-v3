# =============================================================================
# File: tools/probe_models.py
# Persistent Assistant v3 – Model Probe (endpoint-aware) with PROGRESS/SUMMARY
# Author: G. Rapson | GR-Analysis
# Created: 2025-08-19 12:40 BST
# Update History:
#   - 2025-08-19 12:40 BST: Endpoint-aware probing; skip non-chat; categorize outcomes.
# =============================================================================

from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import os, sys, json, yaml, time, datetime
from typing import Dict, Any
from openai import OpenAI
import anthropic
from tools._env import load_keys
from tools.model_classifier import classify

CATALOGUE = "ai_models.yaml"
HEALTH_OUT = "ai_models_health.yaml"
TMP_OUT = "ai_models_tmp.yaml"

KEYS = load_keys()

def _load_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return yaml.safe_load(f) or {}

def _save_yaml(data: Dict[str, Any], path: str) -> None:
    d = os.path.dirname(os.path.abspath(path)); os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

def _probe_openai_chat(model: str) -> Dict[str, Any]:
    t0=time.perf_counter()
    try:
        client = OpenAI(api_key=KEYS.get("openai"))
        r = client.chat.completions.create(
            model=model, messages=[{"role":"user","content":"ping"}], temperature=0, max_tokens=8
        )
        ok = bool(getattr(r, "choices", None))
        return {"probe_ok": ok, "category": "ok" if ok else "fail",
                "latency_ms": round((time.perf_counter()-t0)*1000,1), "error": ""}
    except Exception as e:
        msg = str(e)
        cat = "permission" if "not allowed" in msg.lower() or "permission" in msg.lower() else "fail"
        return {"probe_ok": False, "category": cat,
                "latency_ms": round((time.perf_counter()-t0)*1000,1), "error": msg}

def _probe_openai_responses(model: str) -> Dict[str, Any]:
    t0=time.perf_counter()
    try:
        client = OpenAI(api_key=KEYS.get("openai"))
        r = client.responses.create(model=model, input="ping", max_output_tokens=8)
        ok = bool(getattr(r, "output", None) or getattr(r, "choices", None))
        return {"probe_ok": ok, "category": "ok" if ok else "fail",
                "latency_ms": round((time.perf_counter()-t0)*1000,1), "error": ""}
    except Exception as e:
        msg = str(e)
        cat = "permission" if "not allowed" in msg.lower() or "permission" in msg.lower() else "fail"
        return {"probe_ok": False, "category": cat,
                "latency_ms": round((time.perf_counter()-t0)*1000,1), "error": msg}

def _probe_anthropic_chat(model: str) -> Dict[str, Any]:
    t0=time.perf_counter()
    try:
        client = anthropic.Anthropic(api_key=KEYS.get("anthropic"))
        _ = client.messages.create(model=model, max_tokens=8, messages=[{"role":"user","content":"ping"}])
        return {"probe_ok": True, "category": "ok", "latency_ms": round((time.perf_counter()-t0)*1000,1), "error": ""}
    except Exception as e:
        msg = str(e)
        cat = "permission" if "not allowed" in msg.lower() or "permission" in msg.lower() else "fail"
        return {"probe_ok": False, "category": cat,
                "latency_ms": round((time.perf_counter()-t0)*1000,1), "error": msg}

def main():
    cat = _load_yaml(CATALOGUE)
    if not cat:
        print("SUMMARY: " + json.dumps({"error": "catalogue_missing"}))
        sys.exit(1)

    pairs = []
    for prov, pdata in (cat.get("providers") or {}).items():
        for model in ((pdata.get("models") or {}).keys()):
            pairs.append((prov, model))

    total = len(pairs)
    counts = {"ok":0,"fail":0,"permission":0,"endpoint_mismatch":0,"not_probed":0}
    health = {"last_tested": datetime.datetime.now(datetime.UTC).isoformat(), "providers": {}}

    for i, (prov, model) in enumerate(pairs, start=1):
        cls = classify(prov, model)
        iface = cls.get("interface")
        route = cls.get("probe_route")

        # Default result
        res = {"probe_ok": False, "category": "not_probed", "latency_ms": None, "error": ""}

        if prov == "openai":
            if route == "chat":
                res = _probe_openai_chat(model)
            elif route == "responses":
                res = _probe_openai_responses(model)
            else:
                res = {"probe_ok": False, "category": "endpoint_mismatch", "latency_ms": None,
                       "error": f"not chat-like ({iface})"}
        elif prov == "anthropic":
            if route == "chat":
                res = _probe_anthropic_chat(model)
            else:
                res = {"probe_ok": False, "category": "endpoint_mismatch", "latency_ms": None,
                       "error": f"not chat-like ({iface})"}
        else:
            res = {"probe_ok": False, "category": "not_probed", "latency_ms": None,
                   "error": "provider not wired"}

        counts[res["category"]] = counts.get(res["category"], 0) + 1

        health.setdefault("providers", {}).setdefault(prov, {}).setdefault("models", {})[model] = {
            "last_probe": datetime.datetime.now(datetime.UTC).isoformat(),
            **res
        }

        # Stream progress
        print("PROGRESS: " + json.dumps({
            "n": i, "m": total,
            "ok": counts["ok"], "fail": counts["fail"],
            "skipped": counts["not_probed"] + counts["endpoint_mismatch"],
            "label": f"{prov}/{model}"
        }, separators=(",",":")))
        sys.stdout.flush()

    # Merge health into catalogue (non-destructive)
    merged = cat
    for prov, pdata in (health.get("providers") or {}).items():
        for model, h in (pdata.get("models") or {}).items():
            try:
                merged["providers"][prov]["models"][model]["health"] = h
            except Exception:
                pass

    _save_yaml(health, HEALTH_OUT)
    _save_yaml(merged, TMP_OUT)

    # Final summary
    print("SUMMARY: " + json.dumps({"totals": counts, "total_models": total}, separators=(",",":")))
    # Keep tmp; validation/promotion is handled by update_ai_models.py
    sys.exit(0)
    
if __name__ == "__main__":
    main()
