import argparse, datetime, subprocess, sys
from pathlib import Path
from apply_common import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root', default=''); a=ap.parse_args()
    root = resolve_repo_root(a.repo_root)
    if not root:
        print('Repo root not found', file=sys.stderr); sys.exit(2)
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M')
    step_id='PA-226'
    branch=f'step/{step_id}-intake-to-devstep'
    git(['checkout','-B',branch], root)
    git(['add','-A'], root)
    git(['commit','-m', f'{step_id}: add intake->devstep CLI + smoke'], root, allow_fail=True)
    git(['push','-u','origin',branch], root, allow_fail=True)
    results = root/f'dev_steps/{step_id}/results'; results.mkdir(parents=True, exist_ok=True)
    junit = results/f'junit_{ts}.xml'; log = results/f'pytest_{ts}.log'
    with open(log,'a',encoding='utf-8') as lf:
        code = subprocess.call([sys.executable,'-m','pytest','tests/smoke/test_intake_to_devstep.py',f'--junitxml={junit}','-q'], cwd=root, stdout=lf, stderr=subprocess.STDOUT)
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
    git(['add', str(results), str(manifest)], root)
    git(['commit','-m', f'{step_id}: publish smoke ({status}) @ {ts}'], root, allow_fail=True)
    git(['push'], root, allow_fail=True)
    print('PA-226 done.')

if __name__=='__main__': main()
