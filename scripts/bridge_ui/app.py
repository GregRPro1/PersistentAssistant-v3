#!/usr/bin/env python3
from __future__ import annotations
import json, time, argparse
from pathlib import Path
from typing import Any, Dict, Optional
from flask import Flask, render_template_string

ROOT = Path(__file__).resolve().parents[2]
STATE_P = ROOT / "_state" / "plan_status.json"
OPS_STATUS_P = ROOT / "reports" / "ops" / "ops_status.json"
LOG_P = ROOT / "tmp" / "bridge_tracker.log"
POLL_SEC = 5
STALE_AMBER = 15.0
STALE_RED = 60.0
CTRL_URL = "http://127.0.0.1:6060/control"

TEMPLATE = """<!doctype html><html><head>
  <meta charset='utf-8'><meta http-equiv='refresh' content='{{ poll_sec }}'>
  <title>Tracker Plan Selector & Bridge</title>
  <style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}.card{border:1px solid #ddd;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}.title{font-size:20px;font-weight:600;margin-bottom:8px}.k{color:#666}.v{font-weight:600}.pill{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600}.ok{background:#e8f5e9;color:#1b5e20}.amber{background:#fff3e0;color:#e65100}.red{background:#ffebee;color:#b71c1c}pre{white-space:pre-wrap;background:#fafafa;border:1px dashed #ddd;padding:8px;border-radius:8px;max-height:260px;overflow:auto}.muted{color:#888;font-size:12px}button{margin-right:8px;padding:6px 10px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer}</style>
</head><body>
  <h1>Tracker Plan Selector & Bridge</h1>
  <div class='grid'>
    <div class='card'>
      <div class='title'>Plan Selector</div>
      <div><span class='k'>selected_plan:</span> <span class='v'>{{ plan.selected_plan }}</span></div>
      <div><span class='k'>last_update:</span> <span class='v'>{{ plan.last_update }}</span> <span class='pill {{ plan.fresh_cls }}'>{{ plan.fresh_txt }}</span></div>
      {% if plan.tasks %}<div class='title' style='margin-top:10px;font-size:16px;'>Tasks</div><ul>{% for t in plan.tasks %}<li>{{ t }}</li>{% endfor %}</ul>{% else %}<div class='muted' style='margin-top:6px;'>No tasks published by tracker.</div>{% endif %}
    </div>
    <div class='card'>
      <div class='title'>Bridge Status</div>
      <div><span class='k'>component:</span> <span class='v'>{{ ops.component }}</span></div>
      <div><span class='k'>status:</span> <span class='v'>{{ ops.status }}</span> <span class='pill {{ ops.fresh_cls }}'>{{ ops.fresh_txt }}</span></div>
      <div class='muted'>updated_at: {{ ops.updated_at }}</div>
    </div>
    <div class='card'>
      <div class='title'>Bridge Log Tail</div>
      {% if log_tail %}<pre>{{ log_tail }}</pre>{% else %}<div class='muted'>No log file found at {{ log_path }}</div>{% endif %}
    </div>
    <div class='card'>
      <div class='title'>Controls</div>
      <button onclick="fetch('{{ ctrl }}?service=heartbeat&action=restart',{method:'POST'})">Restart Heartbeat</button>
      <button onclick="fetch('{{ ctrl }}?service=planrefresher&action=restart',{method:'POST'})">Restart Plan</button>
      <button onclick="fetch('{{ ctrl }}?service=bridgeui&action=restart',{method:'POST'})">Restart UI</button>
    </div>
  </div>
  <div class='muted' style='margin-top:16px;'>Auto-refreshes every {{ poll_sec }}s. Staleness: ≤{{ amber }}s OK, ≤{{ red }}s AMBER, >{{ red }}s RED.</div>
</body></html>"""

def _read_json(p: Path):
    try:
        with p.open("r", encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def _freshness(ts, mtime):
    now = time.time()
    if ts and 0 < ts < now + 86400*365: return max(0.0, now - ts)
    if mtime: return max(0.0, now - mtime)
    return float("inf")

def _age_to_class(age: float):
    if age <= STALE_AMBER: return "ok", "FRESH"
    if age <= STALE_RED: return "amber", f"STALE {age:.0f}s"
    return "red", f"OLD {age:.0f}s"

def create_app():
    app = Flask(__name__)
    @app.get('/')
    def index():
        plan_raw = _read_json(STATE_P) or {}
        ts = None
        for k in ('updated_ts','last_update_ts','last_heartbeat_ts'):
            if isinstance(plan_raw.get(k), (int,float)): ts = float(plan_raw.get(k)); break
        mtime = STATE_P.stat().st_mtime if STATE_P.exists() else None
        age = _freshness(ts, mtime); plan_cls, plan_txt = _age_to_class(age)
        selected = plan_raw.get('selected_plan') or plan_raw.get('plan') or 'Unknown'
        tasks = plan_raw.get('tasks') if isinstance(plan_raw.get('tasks'), list) else []

        ops_raw = _read_json(OPS_STATUS_P) or {}
        ots = None
        for k in ('updated_ts','last_heartbeat_ts','heartbeat_ts'):
            if isinstance(ops_raw.get(k), (int,float)): ots = float(ops_raw.get(k)); break
        omtime = OPS_STATUS_P.stat().st_mtime if OPS_STATUS_P.exists() else None
        oage = _freshness(ots, omtime); ops_cls, ops_txt = _age_to_class(oage)
        component = ops_raw.get('component','bridge'); status = ops_raw.get('status','unknown'); updated_at = ops_raw.get('updated_at','')

        tail = None
        if LOG_P.exists():
            try:
                with LOG_P.open('r', encoding='utf-8', errors='ignore') as f: tail = ''.join(f.readlines()[-200:])
            except Exception: tail = None

        return render_template_string(TEMPLATE,
            poll_sec=POLL_SEC, amber=int(STALE_AMBER), red=int(STALE_RED), ctrl=CTRL_URL,
            plan={"selected_plan": selected, "last_update": time.strftime('%Y-%m-%d %H:%M:%S'),
                  "fresh_cls": plan_cls, "fresh_txt": plan_txt, "tasks": tasks},
            ops={"component": component, "status": status, "fresh_cls": ops_cls, "fresh_txt": ops_txt, "updated_at": updated_at},
            log_tail=tail, log_path=str(LOG_P)
        )
    return app

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=5070)
    args = ap.parse_args()
    app = create_app()
    print(f'[UI] Serving on http://{args.host}:{args.port}')
    app.run(host=args.host, port=args.port, debug=False)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
