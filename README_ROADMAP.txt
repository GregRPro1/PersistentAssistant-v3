# PAL Roadmap Consolidator

Installs `scripts/tools/consolidate_roadmap.py` which scans the repo for all plan/tracker/context files
and generates a single canonical roadmap with historic items preserved, descriptive text, and sign-off criteria.

## Usage (PowerShell)
```powershell
# From repo root
python .\scripts\tools\consolidate_roadmap.py

# Optional flags
python .\scripts\tools\consolidate_roadmap.py --include-context --min-phase R1 --active 13D
```

## Outputs
- `plans\roadmap\consolidated_roadmap.yaml`  (canonical, richly structured)
- `plans\roadmap\roadmap_summary.csv`        (flat table for quick review)
- `plans\roadmap\roadmap_report.md`         (human-readable report)
- `reports\roadmap_duplicates.json`          (duplicate detection details)

## Smoke test
```powershell
python .\scripts\smoke\smoke_roadmap_coherence.py
```
