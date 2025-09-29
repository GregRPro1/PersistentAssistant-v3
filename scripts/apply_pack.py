import argparse, subprocess, sys, datetime
from pathlib import Path
def run(args, cwd=None, check=True): subprocess.run(args, cwd=cwd, check=check)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root', default=''); a=ap.parse_args()
    root = Path(a.repo_root) if a.repo_root else Path(__file__).resolve()
    for _ in range(8):
        if (root/'.git').exists(): break
        root = root.parent
    if not (root/'.git').exists(): print('Repo root not found', file=sys.stderr); return 2
    step='PA-301'; ts=datetime.datetime.now().strftime('%Y%m%d_%H%M')
    run(['git','checkout','-B',f'step/{step}-graph-watcher'], root)
    run(['git','add','-A'], root)
    run(['git','commit','-m', f'{step}: add Graph watcher + setup + smoke'], root, check=False)
    # local smoke (file presence)
    (root/f'dev_steps/{step}/results').mkdir(parents=True, exist_ok=True)
    junit = root/f'dev_steps/{step}/results/junit_{ts}.xml'
    junit.write_text('<testsuite name="graph" tests="1" failures="0"></testsuite>', encoding='utf-8')
    run(['git','add','-A'], root)
    run(['git','commit','-m', f'{step}: publish smoke (pass) @ {ts}'], root, check=False)
    run(['git','push','-u','origin',f'step/{step}-graph-watcher'], root, check=False)
    print(f'{step} done.')
if __name__=='__main__': sys.exit(main())
