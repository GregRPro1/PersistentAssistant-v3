from __future__ import annotations
import sys, platform, shutil, json, pathlib

def main() -> int:
    info = {
        "python_version": sys.version.split()[0],
        "python_exe": sys.executable,
        "platform": platform.platform(),
        "venv": str(pathlib.Path(sys.prefix)),
        "has_git": shutil.which("git") is not None,
        "has_pytest": shutil.which("pytest") is not None,
    }
    print(json.dumps(info, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main()))
