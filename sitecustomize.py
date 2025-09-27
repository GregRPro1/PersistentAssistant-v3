# sitecustomize.py — ensure repo root on sys.path for tests/tools
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
p = str(ROOT)
if p not in sys.path:
    sys.path.insert(0, p)
