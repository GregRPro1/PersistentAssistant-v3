from __future__ import annotations
# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml, os
from pathlib import Path
INS = Path("data/insights/model_probe_status.yaml")
OUT= Path("data/insights/ai_summary_line.txt")

def main():
    if not INS.exists():
        OUT.write_text("AI Interfaces — status unavailable (no probes yet).",encoding="utf-8"); return
    d = yaml.safe_load(INS.read_text(encoding="utf-8")) or {}
    provs = (d.get("providers") or {})
    p_count = len(provs)
    models_total=0
    buckets={"chat": [0,0,0], "image":[0,0,0], "audio":[0,0,0], "other":[0,0,0]}
    def inc(bucket, status):
        # indexes: green, amber, red
        if status=="success": buckets[bucket][0]+=1
        elif status in ("partial","unknown"): buckets[bucket][1]+=1
        elif status in ("error","fail"): buckets[bucket][2]+=1
        else: buckets[bucket][1]+=1
    for p, pd in provs.items():
        for mid, md in (pd.get("models") or {}).items():
            models_total+=1
            caps = (md.get("capabilities") or [])
            status = (md.get("status") or "unknown").lower()
            bucket = "other"
            if "chat" in caps: bucket="chat"
            elif "image" in caps: bucket="image"
            elif "audio" in caps: bucket="audio"
            inc(bucket, status)
    line = (f"AI Interfaces — Providers: {p_count}; Models: {models_total}; "
            f"Chat G/A/R: {buckets['chat'][0]}/{buckets['chat'][1]}/{buckets['chat'][2]}; "
            f"Image G/A/R: {buckets['image'][0]}/{buckets['image'][1]}/{buckets['image'][2]}; "
            f"Audio G/A/R: {buckets['audio'][0]}/{buckets['audio'][1]}/{buckets['audio'][2]}; "
            f"Other G/A/R: {buckets['other'][0]}/{buckets['other'][1]}/{buckets['other'][2]}")
    OUT.write_text(line, encoding="utf-8")
    print(line)

if __name__ == "__main__":
    main()
