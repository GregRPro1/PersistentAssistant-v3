#!/usr/bin/env python3
import yaml, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
f = ROOT / "plans" / "roadmap" / "consolidated_roadmap.yaml"
if not f.exists():
    print("[FAIL] consolidated_roadmap.yaml missing"); sys.exit(2)
data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
items = data.get("items", [])
if not items:
    print("[WARN] roadmap is empty"); sys.exit(1)
ids = [i.get("id") for i in items]
if len(ids) != len(set(ids)):
    print("[WARN] duplicate IDs in consolidated roadmap")
    sys.exit(1)
print("[OK] roadmap coherent with", len(items), "items")
sys.exit(0)
