import json
from pathlib import Path
from xml.etree import ElementTree as ET
def parse_junit(p: Path):
    root=ET.parse(p).getroot()
    suites=root.findall('testsuite') if root.tag!='testsuite' else [root]
    tot=err=fail=skip=0
    for s in suites:
        tot += int(s.attrib.get('tests',0)); err += int(s.attrib.get('errors',0)); fail += int(s.attrib.get('failures',0)); skip += int(s.attrib.get('skipped',0))
    return tot, err, fail, skip
def collect(dev_steps: Path):
    rows=[]
    for d in sorted(dev_steps.glob('PA-*')):
        junit=None; res=d/'results'
        if res.exists():
            cands=sorted(res.glob('junit_*.xml'), key=lambda p: p.stat().st_mtime, reverse=True)
            if cands: junit=cands[0]
        if not junit: continue
        tot,err,fail,skip=parse_junit(junit)
        rows.append({'step': d.name, 'total': tot, 'errors': err, 'failures': fail, 'skips': skip})
    return rows
def ascii_table(rows):
    if not rows: return 'No smoke artifacts found.'
    hdr='| Step | Total | Failures | Errors | Skips |\n|---|---:|---:|---:|---:|'
    lines=[hdr]+[f"| {r['step']} | {r['total']} | {r['failures']} | {r['errors']} | {r['skips']} |" for r in rows]
    return '\n'.join(lines)
def write_html(rows, out_html: Path):
    out_html.parent.mkdir(parents=True, exist_ok=True)
    def status(r): return 'pass' if (r['failures']==0 and r['errors']==0) else 'fail'
    rows2=[{**r,'status':status(r)} for r in rows]
    table_rows='\n'.join([f"<tr><td>{r['step']}</td><td>{r['total']}</td><td>{r['failures']}</td><td>{r['errors']}</td><td>{r['skips']}</td><td>{r['status']}</td></tr>" for r in rows2])
    html = "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Smoke Summary</title>" \
           "<style>body{font-family:Segoe UI,Arial,sans-serif} table{border-collapse:collapse} " \
           "td,th{border:1px solid #ccc;padding:6px 10px} th{background:#f3f3f3}</style>" \
           "</head><body><h2>Smoke Summary</h2><table><thead><tr>" \
           "<th>Step</th><th>Total</th><th>Failures</th><th>Errors</th><th>Skips</th><th>Status</th>" \
           "</tr></thead><tbody>" + table_rows + "</tbody></table></body></html>"
    out_html.write_text(html, encoding='utf-8')
def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--dev-steps', default='dev_steps'); ap.add_argument('--out-html', default='reports/smoke/index.html')
    a=ap.parse_args(); rows=collect(Path(a.dev_steps)); print(ascii_table(rows)); write_html(rows, Path(a.out_html))
if __name__=='__main__': main()
