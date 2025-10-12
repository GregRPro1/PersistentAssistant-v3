from utils.context_banner import print_banner
print_banner("PAL")
import runpy, pathlib
repo_root = pathlib.Path(__file__).resolve().parents[1]
server_path = repo_root / "current" / "server.py"
runpy.run_path(str(server_path), run_name="__main__")
