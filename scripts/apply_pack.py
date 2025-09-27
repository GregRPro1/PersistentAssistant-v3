import argparse, datetime, subprocess, sys
from pathlib import Path
from apply_common import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root', default=''); a=ap.parse_args()
    root = resolve_repo_root(a.repo_root)
    if not root:
        print('Repo root not found', file=sys.stderr); sys.exit(2)
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M')
    step_id='PA-234'
    commit_msg = "email watcher (imap+local) + scheduler + smoke"
    slug = slugify_branch(commit_msg)
    branch=f'step/{step_id}-' + slug
    git(['checkout','-B',branch], root)
    git(['add','-A'], root)
    git(['commit','-m', f'{step_id}: stage files'], root, allow_fail=True)
    results = root/f'dev_steps/{step_id}/results'; results.mkdir(parents=True, exist_ok=True)
    junit = results/f'junit_{ts}.xml'; log = results/f'pytest_{ts}.log'
    with open(log,'a',encoding='utf-8') as lf:
        code = subprocess.call([sys.executable,'-m','pytest','tests/smoke/test_email_watcher_local.py',f'--junitxml={junit}','-q'], cwd=root, stdout=lf, stderr=subprocess.STDOUT)
    smoke = results / f'smoke_{ts}.zip'
    zip_files(smoke, [junit, log], root)
    manifest = root/f'dev_steps/{step_id}/manifest.yaml'
    status = 'pass' if code==0 else 'fail'
    sha = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
    block = "# updated smoke at {ts}\nlatest:\n  smoke_zip: \"{smoke_zip}\"\n  status: \"{status}\"\n  commit_sha: \"{sha}\"\n  updated_at: \"{ts}\"\n".format(
        ts=ts, smoke_zip=smoke.relative_to(root).as_posix(), status=status, sha=sha
    )
    with open(manifest,'a',encoding='utf-8') as f: f.write(block)
    git(['add','-A'], root)
    git(['commit','-m', f'{step_id}: publish smoke ({status}) @ {ts}'], root, allow_fail=True)
    git(['push','-u','origin',branch], root, allow_fail=True)
    print(f'{step_id} done.')

if __name__=='__main__': main()
