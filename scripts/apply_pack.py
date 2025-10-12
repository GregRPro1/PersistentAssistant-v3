#!/usr/bin/env python3
import os, shutil, subprocess, sys, datetime

REPO = r"C:\_Repos\PersistentAssistant"

def copytree_force(src, dst):
    os.makedirs(dst, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        outdir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(outdir, exist_ok=True)
        for fn in files:
            s = os.path.join(root, fn)
            d = os.path.join(outdir, fn)
            if os.path.abspath(s) == os.path.abspath(d):
                continue
            shutil.copy2(s, d)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    payload = os.path.normpath(os.path.join(here, "..", "payload"))
    if not os.path.isdir(REPO): raise SystemExit(f"Repo root not found: {REPO}")
    # create branch and copy payload folders
    subprocess.run(["git","-C",REPO,"checkout","-B","step/PAL20251012A-python-watchdog"], check=False)
    # payload files
    copytree_force(os.path.join(payload, "watchdog"), os.path.join(REPO, "watchdog"))
    copytree_force(os.path.join(payload, "scripts"), os.path.join(REPO, "scripts"))
    shutil.copy2(os.path.join(payload, "pal_project_plan.yaml"), os.path.join(REPO, "pal_project_plan.yaml"))
    # commit
    subprocess.run(["git","-C",REPO,"add","watchdog","scripts","pal_project_plan.yaml"], check=False)
    subprocess.run(["git","-C",REPO,"commit","-m","PAL20251012A: Python watchdog, plan, payload-only apply"], check=False)
    print("=== PACK/STATUS: Python apply completed ===")

if __name__ == "__main__":
    main()
