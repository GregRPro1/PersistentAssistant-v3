import hashlib, sys
from pathlib import Path
def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()
def main():
    if len(sys.argv)<2:
        print("usage: sha256sum.py <file>"); sys.exit(2)
    p = Path(sys.argv[1])
    if not p.exists():
        print("not found:", p); sys.exit(2)
    print(sha256_file(p))
if __name__=='__main__':
    main()
