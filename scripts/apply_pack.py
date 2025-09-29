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
    (root/'tools/py').mkdir(parents=True, exist_ok=True)
    (root/'tools/py/email_watcher.py').write_text("""REPLACED_BY_PACK""")
    (root/'tools/py/which_email_module.py').write_text("""REPLACED_BY_PACK""")
    run(['git','checkout','-B',f'step/{step}-fix-annot'], root)
    run(['git','add','-A'], root)
    run(['git','commit','-m', f'{step}: fix watcher annotation + add which_email_module.py'], root, check=False)
    run(['git','push','-u','origin',f'step/{step}-fix-annot'], root, check=False)
    print(f'{step} done.')
if __name__=='__main__': sys.exit(main())
