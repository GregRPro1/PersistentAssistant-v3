import os, runpy
ROOT = os.path.abspath(os.getcwd())
runpy.run_path(os.path.join(ROOT, "tools", "leb_ensure.py"), run_name="__main__")
