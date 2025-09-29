import subprocess
from pathlib import Path

FILES = {'tools/ps1/run_control_server.ps1': "param([string]$Host='127.0.0.1',[int]$Port=8776)\n$ErrorActionPreference='Stop'\n$u = \"http://$($Host):$($Port)/control/\"\nWrite-Host \"Starting PA Control standalone at $u\"\npython (Join-Path $PSScriptRoot '..\\py\\control_server.py') --host $Host --port $Port\n"}

def write(root: Path, rel: str, txt: str):
    p = root/rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding='utf-8')

def find_root(seed: Path) -> Path:
    p = seed
    for _ in range(12):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p = p.parent
    return seed

def run(a, cwd=None, check=False):
    subprocess.run(a, cwd=cwd, check=check)

def main():
    root = find_root(Path(__file__).resolve())
    for rel,txt in FILES.items():
        write(root, rel, txt)
    try: run(['git','checkout','-B','step/PA-331-control-standalone'], root)
    except Exception: pass
    run(['git','add','-A'], root)
    run(['git','commit','-m','PA-331: fix run_control_server.ps1 interpolation'], root)
    run(['git','push','-u','origin','step/PA-331-control-standalone'], root)
    print('Hotfix applied. Now run: pwsh tools\\ps1\\run_control_server.ps1')

if __name__=='__main__':
    main()