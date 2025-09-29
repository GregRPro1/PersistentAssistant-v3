
import argparse, subprocess, sys, datetime
from pathlib import Path
def run(a, cwd=None, check=True): subprocess.run(a, cwd=cwd, check=check)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root', default=''); a=ap.parse_args()
    root = Path(a.repo_root) if a.repo_root else Path(__file__).resolve()
    for _ in range(8):
        if (root/'.git').exists(): break
        root = root.parent
    if not (root/'.git').exists():
        print('Repo root not found', file=sys.stderr); return 2
    step='PA-302'; ts=datetime.datetime.now().strftime('%Y%m%d_%H%M')
    run(['git','checkout','-B',f'step/{step}-email-watcher-refactor'], root)
    run(['git','add','-A'], root)
    run(['git','commit','-m', f'{step}: refactor email_watcher.py + smokes'], root, check=False)
    (root/f'dev_steps/{step}/results').mkdir(parents=True, exist_ok=True)
    junit = root/f'dev_steps/{step}/results/junit_{ts}.xml'
    log = root/f'dev_steps/{step}/results/pytest_{ts}.log'
    code = subprocess.call([sys.executable,'-m','pytest','-q',
                            'tests/smoke/test_email_watcher_import.py',
                            'tests/smoke/test_email_watcher_yaml_placeholder.py',
                            f'--junitxml={junit}'], cwd=root,
                            stdout=open(log,'w',encoding='utf-8'),
                            stderr=subprocess.STDOUT)
    from zipfile import ZipFile, ZIP_DEFLATED
    smoke = root/f'dev_steps/{step}/results'/f'smoke_{ts}.zip'
    with ZipFile(smoke,'w',compression=ZIP_DEFLATED) as Z:
        if junit.exists(): Z.write(junit, junit.relative_to(root).as_posix())
        if log.exists(): Z.write(log, log.relative_to(root).as_posix())
    manifest = root/f'dev_steps/{step}/manifest.yaml'
    status = 'pass' if code==0 else 'fail'
    sha = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
    block = "# updated smoke at {ts}\nlatest:\n  smoke_zip: \"{smoke_zip}\"\n  status: \"{status}\"\n  commit_sha: \"{sha}\"\n  updated_at: \"{ts}\"\n".format(
        ts=ts, smoke_zip=smoke.relative_to(root).as_posix(), status=status, sha=sha
    )
    with open(manifest,'a',encoding='utf-8') as f: f.write(block)
    run(['git','add','-A'], root)
    run(['git','commit','-m', f'{step}: publish smoke ({status}) @ {ts}'], root, check=False)
    run(['git','push','-u','origin',f'step/{step}-email-watcher-refactor'], root, check=False)
    print(f'{step} done.')
if __name__=='__main__': sys.exit(main())
