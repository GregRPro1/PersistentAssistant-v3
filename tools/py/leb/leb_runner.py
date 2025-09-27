import os, runpy
ROOT = os.path.abspath(os.getcwd())
runpy.run_path(os.path.join(ROOT, "tools", "leb_runner.py"), run_name="__main__")
