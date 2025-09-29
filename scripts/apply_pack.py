import subprocess
from pathlib import Path
import base64

FILES = {
  'tools/py/patch_unified_add_control.py': '"# tools/py/patch_unified_add_control.py\\n# Add \'server.control_console\' into config/unified_server.yaml candidates without requiring PyYAML.\\nimport re\\nfrom pathlib import Path\\n\\nTARGET = \'server.control_console\'\\n\\ndef find_root(seed: Path) -> Path:\\n    p = seed\\n    for _ in range(12):\\n        if (p/\'.git\').exists(): return p\\n        if p.parent==p: break\\n        p = p.parent\\n    return seed\\n\\ndef ensure_candidate(txt: str) -> str:\\n    if TARGET in txt:\\n        return txt\\n    # If there\'s a candidates: YAML list, insert \'- server.control_console\' after it.\\n    m = re.search(r\'(?m)^(?P<indent>\\\\s*)candidates\\\\s*:\\\\s*(?:#.*)?$\', txt)\\n    if m:\\n        indent = m.group(\'indent\')\\n        # Find where the list ends (next non-indented key or end of file)\\n        start = m.end()\\n        # Look ahead for the next top-level key (same or less indent and ends with \':\')\\n        tail = txt[start:]\\n        lines = tail.splitlines(True)\\n        insert_pos = start\\n        for i, line in enumerate(lines):\\n            if re.match(rf\'(?m)^[^\\\\S\\\\r\\\\n]*\\\\S\', line) and not line.startswith(indent + \'  -\'):\\n                # If this looks like a new key at same or less indent, stop\\n                if re.match(rf\'^{indent}\\\\S.*:\\\\s*\', line):\\n                    break\\n            insert_pos += len(line)\\n        insertion = f\'\\\\n{indent}  - {TARGET}\\\\n\'\\n        return txt[:start] + insertion + txt[start:]\\n    # If no candidates block, create one at end\\n    add = f\'\\\\n# added by patch_unified_add_control.py\\\\ncandidates:\\\\n  - {TARGET}\\\\n\'\\n    return txt + add\\n\\ndef main():\\n    root = find_root(Path(__file__).resolve())\\n    cfg = root/\'config\'/\'unified_server.yaml\'\\n    if not cfg.exists():\\n        return\\n    txt = cfg.read_text(encoding=\'utf-8\')\\n    new = ensure_candidate(txt)\\n    if new != txt:\\n        cfg.write_text(new, encoding=\'utf-8\')\\n\\nif __name__==\'__main__\':\\n    main()"',
  'tools/ps1/run_smoke_control.ps1': '"param([string]$Pattern=\'control\')\\n$ErrorActionPreference=\'Stop\'\\nWrite-Host \\"Running smoke tests matching: $Pattern\\"\\n$py = Join-Path $PSScriptRoot \'..\\\\..\\\\..\\\\.venv\\\\Scripts\\\\python.exe\'\\nif (-not (Test-Path $py)) { $py = \'python\' }\\n& $py -m pytest -q (\\"tests\\\\smoke\\\\test_*${Pattern}*.py\\")\\n"',
  'tools/ps1/open_unified_in_edge.ps1': '"param([string]$Host=\'127.0.0.1\',[int]$Port=8765,[switch]$Control)\\n$ErrorActionPreference=\'Stop\'\\n$path = if ($Control) { \\"/control/\\" } else { \\"/\\" }\\n$url = \\"http://$($Host):$($Port)$path\\"\\n$edge = Get-Command \'msedge.exe\' -ErrorAction SilentlyContinue\\nif ($edge) { Start-Process -FilePath $edge.Source -ArgumentList $url; exit 0 }\\n$path1 = \'C:\\\\Program Files (x86)\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe\'\\n$path2 = \'C:\\\\Program Files\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe\'\\nif (Test-Path $path1) { Start-Process -FilePath $path1 -ArgumentList $url; exit 0 }\\nif (Test-Path $path2) { Start-Process -FilePath $path2 -ArgumentList $url; exit 0 }\\nStart-Process \\"cmd\\" \\"/c start $url\\"\\n"',
}

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
    for rel, txt in FILES.items():
        write(root, rel, txt)
    # Run the patcher (safe even without PyYAML)
    run(['python', str(root/'tools/py/patch_unified_add_control.py')], root, check=False)
    try: run(['git','checkout','-B','step/PA-333-control-fix3'], root)
    except Exception: pass
    run(['git','add','-A'], root)
    run(['git','commit','-m','PA-333: patch unified candidates (no PyYAML), smoke runner, Edge opener'], root)
    run(['git','push','-u','origin','step/PA-333-control-fix3'], root)
    print('PA-333 applied.')
    print('Smokes:   pwsh tools\\ps1\\run_smoke_control.ps1')
    print('Open UI:  pwsh tools\\ps1\\open_unified_in_edge.ps1 -Control')
if __name__=='__main__': main()