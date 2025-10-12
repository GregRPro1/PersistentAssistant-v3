#!/usr/bin/env python3
import subprocess, sys, os, datetime
from pathlib import Path

def run(cmd, cwd=None, check=False):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)

def commit_and_push(repo: Path, message: str):
    run(["git","add","logs","-f"], cwd=repo)
    if (repo/"logs"/"smoke").exists():
        run(["git","add","logs/smoke","-f"], cwd=repo)
    run(["git","commit","-m", message], cwd=repo)
    # push current HEAD to its upstream
    run(["git","push"], cwd=repo)
