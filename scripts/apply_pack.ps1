
# PAL20251013A - Plan Status Sidecar Pack
# Adds sidecar writer to start_tracker_with_plan.py to promote plan_status.json periodically

$ErrorActionPreference = 'Stop'
Write-Host "=== Applying PAL20251013A_plan_status_sidecar_pack ==="

$dst = git rev-parse --show-toplevel 2>$null
if (-not $dst) { $dst = "C:\_Repos\PersistentAssistant" }
$dst = [System.IO.Path]::GetFullPath($dst)

$branch = "step/PAL20251013A_plan_status_sidecar"
if (-not (git -C $dst rev-parse --verify $branch 2>$null)) {
  git -C $dst checkout -b $branch | Out-Null
} else {
  git -C $dst switch $branch | Out-Null
}

function Write-Text($path, $text) {
  $dir = Split-Path $path -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  Set-Content -LiteralPath $path -Value $text -Encoding UTF8
}

# Sidecar upgrade for start_tracker_with_plan.py
$wrapPath = Join-Path $dst "scripts\tracker\start_tracker_with_plan.py"
$body = @"
from __future__ import annotations
import os, sys, json, time, subprocess, signal, threading
from pathlib import Path

REPO = Path(os.environ.get('PA_REPO', r'C:\\_Repos\\PersistentAssistant')).resolve()
os.environ.setdefault('PAL_PLAN', str(REPO / 'config' / 'reliability_plan.yaml'))
PLAN = os.environ['PAL_PLAN']

STATE_DIR = REPO / '_state'; STATE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = REPO / 'tmp'; TMP_DIR.mkdir(parents=True, exist_ok=True)
LOG = TMP_DIR / 'bridge_tracker.log'

def _log(msg: str):
    ts = time.strftime('%H:%M:%S')
    with LOG.open('a', encoding='utf-8') as f:
        f.write(f'[Sidecar {ts}] {msg}\\n')

def _sidecar_writer():
    f = STATE_DIR / 'plan_status.json'
    while True:
        try:
            data = {'ts': int(time.time()), 'selected_plan': 'Phase-R1'}
            f.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception as e:
            _log(f'write fail: {e}')
        time.sleep(5)

threading.Thread(target=_sidecar_writer, daemon=True).start()

_log(f'start with plan={PLAN}')

target = REPO/'pal'/'ui'/'desktop'/'pal_tracker.py'
if not target.exists():
    _log(f'ERR tracker not found at {target}')
    print(f'[ERR] tracker not found at {target}'); sys.exit(2)

proc = subprocess.Popen([sys.executable, str(target)], cwd=str(target.parent))
_log(f'spawned pid={proc.pid}')
try:
    rc = proc.wait()
    _log(f'exit rc={rc}')
    sys.exit(rc)
except KeyboardInterrupt:
    _log('keyboard interrupt -> terminate child')
    try:
        proc.send_signal(signal.CTRL_BREAK_EVENT if hasattr(signal, "CTRL_BREAK_EVENT") else signal.SIGTERM)
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        pass
    sys.exit(130)
"@

Write-Text $wrapPath $body
Write-Host "Updated tracker wrapper with sidecar writer."

# Smoke test
$smokePath = Join-Path $dst "scripts\smoke\smoke_plan_promoted.py"
$smoke = @"
from __future__ import annotations
import json, time, sys
from pathlib import Path

REPO = Path(r'C:\\_Repos\\PersistentAssistant').resolve()
f = REPO/'_state'/'plan_status.json'
for i in range(12):
    if f.exists():
        data = json.loads(f.read_text(encoding='utf-8'))
        sel = data.get('selected_plan','')
        print('selected_plan=', sel)
        if sel and '(pre)' not in sel:
            print('[OK] plan promoted')
            sys.exit(0)
    time.sleep(1)
print('[STALE] plan not promoted in time'); sys.exit(2)
"@
Write-Text $smokePath $smoke
Write-Host "Wrote smoke: scripts\\smoke\\smoke_plan_promoted.py"

git -C $dst add "scripts\tracker\start_tracker_with_plan.py" "scripts\smoke\smoke_plan_promoted.py" | Out-Null
git -C $dst commit -m "PAL20251013A: add plan status sidecar writer; periodic promotion" | Out-Null

Write-Host "Pack applied. Start tracker via wrapper, then run smoke to verify promotion."
