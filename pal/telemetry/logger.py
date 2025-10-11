"""
Simple telemetry logger (cost/time per task/PR).
Writes CSV and JSON lines to reports/telemetry.
"""
from pathlib import Path
import time, json, csv
from dataclasses import dataclass, asdict

OUT = Path("reports/telemetry")
OUT.mkdir(parents=True, exist_ok=True)

@dataclass
class TelemetryEvent:
    ts: str
    kind: str   # e.g., "task", "pr"
    id: str
    seconds: float = 0.0
    tokens: int = 0
    cost_usd: float = 0.0
    notes: str = ""

def log_event(ev: TelemetryEvent):
    OUT.mkdir(parents=True, exist_ok=True)
    # JSONL
    with (OUT / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
    # CSV
    new = not (OUT / "events.csv").exists()
    with (OUT / "events.csv").open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(ev).keys()))
        if new: w.writeheader()
        w.writerow(asdict(ev))
