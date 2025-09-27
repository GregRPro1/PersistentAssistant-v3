import argparse, json, xml.etree.ElementTree as ET
from pathlib import Path

def find_latest_junit(result_dir: Path):
    latest=None
    for p in result_dir.rglob('junit_*.xml'):
        if latest is None or p.stat().st_mtime > latest.stat().st_mtime:
            latest=p
    return latest

def parse_junit(p: Path):
    try:
        t=ET.parse(p).getroot()
        suites=t.findall('testsuite') if t.tag!='testsuite' else [t]
        total=errors=failures=skips=0
        for s in suites:
            total += int(s.attrib.get('tests',0))
            errors += int(s.attrib.get('errors',0))
            failures += int(s.attrib.get('failures',0))
            skips += int(s.attrib.get('skipped',0))
        return {'total':total,'errors':errors,'failures':failures,'skips':skips}
    except Exception:
        return {'total':0,'errors':0,'failures':0,'skips':0}

def aggregate(results_root: Path):
    rows=[]
    for step_dir in sorted(results_root.glob('PA-*')):
        res_dir = step_dir/'results'
        junit = find_latest_junit(res_dir)
        if not junit: continue
        stats = parse_junit(junit)
        rows.append({'step': step_dir.name, 'junit': junit.as_posix(), **stats})
    return rows

def write_outputs(rows, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir/'summary.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    lines=['| Step | Total | Failures | Errors | Skips |','|---|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['step']} | {r['total']} | {r['failures']} | {r['errors']} | {r['skips']} |")
    (out_dir/'summary.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results-root', default='dev_steps'); ap.add_argument('--out-dir', default='reports/smoke')
    a=ap.parse_args(); rows=aggregate(Path(a.results_root)); write_outputs(rows, Path(a.out_dir))

if __name__=='__main__': main()
