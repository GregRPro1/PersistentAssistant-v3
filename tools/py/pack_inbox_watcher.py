import argparse, os
from pathlib import Path

def scan_once(src: Path):
    src = Path(src)
    if not src.exists(): return []
    return [p for p in src.glob('PA_*/*.zip')] + [p for p in src.glob('PA_*.zip')] + [p for p in src.glob('PA_OUTPUT_*.zip')]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scan-once', default='')
    a=ap.parse_args()
    if a.scan_once:
        for p in scan_once(Path(a.scan_once)):
            print(p)
    else:
        print('Usage: --scan-once <dir>')

if __name__=='__main__': main()
