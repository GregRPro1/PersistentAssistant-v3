import os, json, glob, datetime, textwrap
ROOT = os.getcwd()
TMP  = os.path.join(ROOT, "tmp")
RUN  = os.path.join(TMP, "run")
FB   = os.path.join(TMP, "feedback")
os.makedirs(RUN, exist_ok=True); os.makedirs(FB, exist_ok=True)

def find_plan(root):
    for base, _, files in os.walk(root):
        if "project_plan_v3.yaml" in files:
            return os.path.join(base, "project_plan_v3.yaml")
    return None

def load_yaml(path):
    try:
        import yaml
    except Exception:
        return None, "PyYAML missing"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}, ""
    except Exception as e:
        return None, str(e)

def summarize_plan(plan):
    out = {"active": None, "next_ids": [], "cursor": None}
    if not isinstance(plan, dict): return out
    st = [plan]; nodes=[]
    while st:
        x = st.pop()
        if isinstance(x, dict):
            nodes.append(x); st.extend(x.values())
        elif isinstance(x, list):
            st.extend(x)
    state = plan.get("state", {})
    out["active"] = state.get("current") or state.get("active_step") or plan.get("active_step")
    act = (out["active"] or "").strip().lower()
    for n in nodes:
        sid = (n.get("id") or n.get("step_id") or "")
        if str(sid).strip().lower() == act:
            cand = n.get("next_ids") or n.get("next") or []
            if isinstance(cand, list): out["next_ids"] = [str(x) for x in cand][:5]
            break
    out["cursor"] = state.get("cursor")
    return out

def collect_tools(root, limit=60):
    tools_dir = os.path.join(root, "tools")
    entries=[]
    if os.path.isdir(tools_dir):
        for p in glob.glob(os.path.join(tools_dir, "**", "*.*"), recursive=True):
            if os.path.isdir(p): continue
            ext  = os.path.splitext(p)[1].lower()
            if ext in (".ps1",".py",".bat",".cmd",".psm1",".sh",".ts",".js",".exe",".dll",".json",".yaml",".yml"):
                name = os.path.relpath(p, root).replace("\\","/")
                entries.append({"path": name})
                if len(entries) >= limit: break
    return entries

def collect_approvals(root):
    ap = os.path.join(root, "tmp", "phone", "approvals")
    out=[]
    if os.path.isdir(ap):
        files = sorted(glob.glob(os.path.join(ap, "approve_*.json")), key=os.path.getmtime, reverse=True)[:10]
        out=[os.path.basename(f) for f in files]
    return out

def read_contract(root):
    p = os.path.join(root, "tools", "assistant_reply_contract.txt")
    try:
        return open(p, "r", encoding="utf-8").read()
    except Exception:
        return "# (contract not found)"

def build_prompt():
    plan_path = find_plan(ROOT)
    plan, perr = (None, None)
    plan_summary = {}
    if plan_path:
        plan, perr = load_yaml(plan_path)
        plan_summary = summarize_plan(plan) if plan is not None else {}
    tools = collect_tools(ROOT)
    approvals = collect_approvals(ROOT)
    contract = read_contract(ROOT)

    header = "You are the assistant powering PersistentAssistant. Follow the reply schema EXACTLY."
    schema = contract

    ctx = {
        "timestamp_utc": datetime.datetime.utcnow().isoformat()+"Z",
        "active_step": plan_summary.get("active"),
        "next_ids_hint": plan_summary.get("next_ids", []),
        "approvals_recent": approvals,
        "tools_sample": tools,
        "root": ROOT.replace("\\","/")
    }

    body = []
    body.append(header)
    body.append("")
    body.append("## Reply Schema (STRICT) — you must reply in this exact shape:")
    body.append(schema)
    body.append("")
    body.append("## Project context snapshot")
    body.append(json.dumps(ctx, ensure_ascii=False, indent=2))
    body.append("")
    body.append("## Your task now")
    body.append(textwrap.dedent("""\
        1) Read the context.
        2) Decide the single best next action toward the active step (or re-align the plan if needed).
        3) Then output ONLY the schema block (no other text). Populate:
           - PACK: absolute pack path you would have created (or [NOT CREATED] if none).
           - STATUS: OK/WARN/FAIL with a very short reason.
           - NEXT: up to 3 concrete next step IDs or actions (strings).
           - BRIEF: 1–3 crisp lines describing what you did / found / or what you need.
           - FS: up to 3 ASCII-only lines of file hints if the human needs to run something.
        4) Do not add any explanations outside the schema fields.
    """))

    prompt = "\n".join(body)
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RUN, f"ai_prompt_{ts}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(out_path)

if __name__ == "__main__":
    build_prompt()
