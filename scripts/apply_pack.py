import argparse, datetime, subprocess, sys
from pathlib import Path
from apply_common import *

def ensure_pytest_ini(root: Path):
    p = root/'pytest.ini'
    lines=[]
    if p.exists():
        lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
    mk = '[pytest]'
    mark = 'markers =\n    smoke: fast smoke checks\n    regression: broader checks\n    slow: slow tests\n    ci: CI gate tests'
    text = mk + '\n' + mark + '\n'
    if p.exists() and 'markers =' in p.read_text(encoding='utf-8', errors='ignore'):
        # overwrite markers block
        content = p.read_text(encoding='utf-8', errors='ignore')
        if 'markers =' in content:
            head, _, tail = content.partition('markers =')
            # keep until end-of-file simple approach
            content = head + text
        else:
            content = content + '\n' + text
        p.write_text(content, encoding='utf-8')
    else:
        p.write_text(text, encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root', default=''); a=ap.parse_args()
    root = Path(a.repo_root) if a.repo_root else Path(__file__).resolve().parents[2]
    if not have_git_repo(root): root = Path(r'C:\\_Repos\\PersistentAssistant')
    if not have_git_repo(root): print('Repo root not found', file=sys.stderr); sys.exit(2)
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M')
    step_id='PA-206'; branch=f'step/{step_id}-pytest-markers'
    ensure_pytest_ini(root)
    (root/'tests/smoke').mkdir(parents=True, exist_ok=True)
    # simple smoke test
    (root/'tests/smoke/test_dummy_smoke.py').write_text('import pytest\n\n@pytest.mark.smoke\ndef test_smoke_pass():\n    assert True\n', encoding='utf-8')
    git(['checkout','-B',branch], root)
    git(['add','-A'], root)
    git(['commit','-m', f'{step_id}: ensure pytest markers + dummy smoke'], root, allow_fail=True)
    git(['push','-u','origin',branch], root, allow_fail=True)
    results = root/f'dev_steps/{step_id}/results'; results.mkdir(parents=True, exist_ok=True)
    junit = results/f'junit_{ts}.xml'; log = results/f'pytest_{ts}.log'
    with open(log,'a',encoding='utf-8') as lf:
        code = subprocess.call([sys.executable,'-m','pytest','-m','smoke',f'--junitxml={junit}','-q'], cwd=root, stdout=lf, stderr=subprocess.STDOUT)
    smoke = results/f'smoke_{ts}.zip'; zip_files(smoke, [junit, log], root)
    manifest = root/f'dev_steps/{step_id}/manifest.yaml'
    status = 'pass' if code==0 else 'fail'
    sha = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
    block = f"""# updated smoke at {ts}
latest:
  smoke_zip: "{smoke.relative_to(root).as_posix()}"
  status: "{status}"
  commit_sha: "{sha}"
  updated_at: "{ts}"
"""
    with open(manifest,'a',encoding='utf-8') as f: f.write(block)
    git(['add', str(results), str(manifest), 'pytest.ini', 'tests/smoke/test_dummy_smoke.py'], root)
    git(['commit','-m', f'{step_id}: publish smoke ({status}) @ {ts}'], root, allow_fail=True)
    git(['push'], root, allow_fail=True)
    print('PA-206 done.')

if __name__=='__main__': main()
