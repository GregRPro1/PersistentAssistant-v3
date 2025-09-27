#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI diagnostics for the Agent PWA.
Checks server health, routes, PWA assets, JS wiring hints, and plan data quality.
Prints a SHORT summary to stdout; writes a full report to tmp\diagnostics\.
"""
import sys, os, json, time, hashlib, re, urllib.request, urllib.error
from urllib.parse import urljoin

BASE = None
TIMEOUT = 8
NOW = time.strftime("%Y%m%d_%H%M%S")
OUTDIR = os.path.join("tmp","diagnostics")
os.makedirs(OUTDIR, exist_ok=True)
FULL = os.path.join(OUTDIR, f"gui_diag_{NOW}.txt")

def get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"Cache-Control":"no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.getcode(), r.headers.get_content_type(), r.read()

def head(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.getcode(), r.headers.get_content_type(), b""

def safe_json(b):
    try: return True, json.loads(b.decode("utf-8","replace"))
    except Exception as e: return False, str(e)

def md5(b): return hashlib.md5(b).hexdigest()

def wfull(s):
    with open(FULL,"a",encoding="utf-8") as f: f.write(s + ("\n" if not s.endswith("\n") else ""))

def summarize_plan(tree):
    total=0; with_text=0; with_items=0; empty=0; sample_empty=[]
    def step_text(node):
        for k in ("text","desc","description","brief","note"):
            v=node.get(k)
            if isinstance(v,str) and v.strip(): return v
        return ""
    def walk(n):
        nonlocal total, with_text, with_items, empty
        total += 1
        t = step_text(n)
        items = n.get("items") or []
        if t: with_text += 1
        if items: with_items += 1
        if (not t) and (not items):
            empty += 1
            if len(sample_empty)<3: sample_empty.append(n.get("id") or n.get("title") or "?")
        for c in (n.get("children") or []): walk(c)
    for n in (tree or []): walk(n)
    return dict(total=total, with_text=with_text, with_items=with_items, empty=empty, sample_empty=sample_empty)

def main():
    global BASE
    host="127.0.0.1"; port="8783"
    # crude arg parse
    for i,a in enumerate(sys.argv[1:]):
        if a=="--host" and i+2<=len(sys.argv): host=sys.argv[i+2]
        if a=="--port" and i+2<=len(sys.argv): port=sys.argv[i+2]
        if a.startswith("--host="): host=a.split("=",1)[1]
        if a.startswith("--port="): port=a.split("=",1)[1]
    BASE=f"http://{host}:{port}/"

    issues=[]
    ok=lambda x: f"[OK] {x}"
    fail=lambda x: issues.append(f"[ISSUE] {x}") or f"[ISSUE] {x}"

    wfull(f"GUI DIAG {NOW} BASE={BASE}")

    # 1) server health
    try:
        code, ctype, body = get(urljoin(BASE,"health"))
        wfull(f"/health code={code} ctype={ctype} body={body[:120]!r}")
        health_ok = (code==200)
    except Exception as e:
        health_ok=False; wfull(f"/health error: {e}")
    print(ok("Server reachable") if health_ok else fail("Server NOT reachable (/health failed)"))

    # 2) routes
    have_routes=False; routes=set()
    try:
        code, ctype, body = get(urljoin(BASE,"__routes__"))
        okjson, j = safe_json(body)
        if okjson:
            for r in j.get("routes",[]):
                rule = r.get("rule"); 
                if rule: routes.add(rule)
            have_routes=True
            wfull(f"routes count={len(routes)}")
        else:
            wfull(f"__routes__ bad json: {j}")
    except Exception as e:
        wfull(f"__routes__ error: {e}")
    print(ok(f"Routes listed: {len(routes)}") if have_routes else fail("Cannot list routes (/__routes__)"))

    def have(path): return path in routes

    # 3) fetch agent page + linked assets
    page_ok=False; html=b""
    try:
        code, ctype, html = get(urljoin(BASE,"pwa/agent"))
        page_ok = (code==200 and "html" in ctype)
        wfull(f"/pwa/agent code={code} ctype={ctype} md5={md5(html)} len={len(html)}")
    except Exception as e:
        wfull(f"/pwa/agent error: {e}")
    print(ok("Agent HTML loaded") if page_ok else fail("Agent HTML not loading"))

    # extract linked scripts/styles we expect
    # tolerate version query strings
    expect = [
        r"/pwa/agent_ui_v3\.css",
        r"/pwa/agent_core_v1\.js",
        r"/pwa/agent_projects_v1\.js",
        r"/pwa/agent_plan_v2\.js",
        r"/pwa/agent_hud_v1\.js",
        r"/pwa/agent_app_v1\.js",
    ]
    found_assets=set()
    text = html.decode("utf-8","replace")
    for pat in expect:
        m = re.search(pat+r"(?:\?v=[^\"'\s>]+)?", text)
        if m: found_assets.add(m.group(0))
    missing = [p for p in expect if not any(re.match(p, a.split("?")[0]) for a in found_assets)]
    if missing:
        fail("Missing asset refs in HTML: " + ", ".join([p.replace("\\","") for p in missing]))
    else:
        print(ok("All expected asset refs present in HTML"))

    # 4) fetch assets, basic sanity
    bad_assets=[]
    for a in sorted(found_assets):
        try:
            code, ctype, body = get(urljoin(BASE, a.lstrip("/")))
            wfull(f"asset {a} code={code} ctype={ctype} len={len(body)} md5={md5(body)}")
            if code!=200 or len(body)<50 or ("text/html" in ctype and b"<title>" in body[:200]):
                bad_assets.append(f"{a} (code {code}, type {ctype}, len {len(body)})")
        except Exception as e:
            bad_assets.append(f"{a} (error {e})")
    if bad_assets: fail("Assets not serving correctly: " + "; ".join(bad_assets))
    else: print(ok("Assets fetch OK"))

    # 5) JS wiring heuristics (string presence)
    wiring_issues=[]
    core = [a for a in found_assets if "agent_core_v1.js" in a]
    app  = [a for a in found_assets if "agent_app_v1.js" in a]
    plan = [a for a in found_assets if "agent_plan_v2.js" in a]
    def fetch(a):
        c, t, b = get(urljoin(BASE, a.lstrip("/"))); return b.decode("utf-8","replace")
    try:
        core_js = fetch(core[0]) if core else ""
        if "window.PA" not in core_js and "win.PA =" not in core_js: wiring_issues.append("core: PA export not found")
        if ".help" not in core_js: wiring_issues.append("core: help button binding not found")
    except: wiring_issues.append("core: cannot read")
    try:
        app_js = fetch(app[0]) if app else ""
        if "PA_APP" not in app_js: wiring_issues.append("app: PA_APP export not found")
        if "refreshSummary" not in app_js: wiring_issues.append("app: summary hook not found")
    except: wiring_issues.append("app: cannot read")
    try:
        plan_js = fetch(plan[0]) if plan else ""
        if "PA_PLAN" not in plan_js: wiring_issues.append("plan: PA_PLAN export not found")
        if "statusIcon" not in plan_js: wiring_issues.append("plan: statusIcon not found")
    except: wiring_issues.append("plan: cannot read")

    if wiring_issues: fail("JS wiring hints: " + "; ".join(wiring_issues))
    else: print(ok("JS wiring signatures present"))

    # 6) endpoint sanity
    def jget(path):
        try:
            code, ctype, body = get(urljoin(BASE,path.lstrip("/")))
            okj, obj = safe_json(body)
            wfull(f"{path} code={code} len={len(body)} json_ok={okj}")
            return (code==200) and okj, obj if okj else {}
        except Exception as e:
            wfull(f"{path} error: {e}")
            return False, {}
    e_ok, _ = jget("agent/summary")
    print(ok("/agent/summary JSON") if e_ok else fail("/agent/summary missing/bad JSON"))

    e_ok, plan_obj = jget("agent/plan")
    if e_ok:
        tree = (((plan_obj or {}).get("plan") or {}).get("tree") or [])
        stats = summarize_plan(tree)
        wfull("plan stats: "+json.dumps(stats))
        msg = f"plan nodes={stats['total']} with_text={stats['with_text']} with_items={stats['with_items']} empty={stats['empty']}"
        if stats["empty"]>0: msg += f" sample_empty={stats['sample_empty']}"
        # expose short plan quality line
        print(ok(msg) if stats["empty"]==0 else fail(msg))
    else:
        fail("/agent/plan missing/bad JSON")

    e_ok,_ = jget("agent/recent")
    print(ok("/agent/recent JSON") if e_ok else fail("/agent/recent missing/bad JSON"))

    e_ok,_ = jget("agent/daily_status")
    print(ok("/agent/daily_status JSON") if e_ok else fail("/agent/daily_status missing/bad JSON"))

    # 7) final brief summary footer
    print("== SUMMARY ==")
    if issues:
        for s in issues: print(s)
        print(f"(Full report: {FULL})")
        sys.exit(2)
    else:
        print("No blocking GUI issues detected from server/asset side.")
        print(f"(Full report: {FULL})")

if __name__=="__main__":
    main()
