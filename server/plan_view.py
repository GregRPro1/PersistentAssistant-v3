import os, re
try: import yaml
except Exception: yaml=None
def _all(x):
  st=[x]
  while st:
    v=st.pop()
    if isinstance(v,dict): yield v; st.extend(list(v.values()))
    elif isinstance(v,list): st.extend(v)
def _class(s):
  s=(s or "").lower()
  if s in ("done","complete","finished"): return "done"
  if s in ("in_progress","active","working","running"): return "in_progress"
  if s in ("blocked","error","fail","failed"): return "blocked"
  return "todo"
def _sum(a,b):
  for k in ("done","in_progress","blocked","todo"): a[k]=a.get(k,0)+b.get(k,0)
  return a
def _count(n):
  c={"done":0,"in_progress":0,"blocked":0,"todo":0}
  if n.get("id"): c[_class(n.get("status"))]+=1
  for ch in n.get("children") or []: _sum(c,_count(ch))
  n["counts"]=c; return c
def _natkey(s):
  import re as _r
  parts=_r.split(r"(\\d+)", str(s))
  return [int(p) if p.isdigit() else p for p in parts]
def build_plan_response(root):
  plan=None
  for b,_,fs in os.walk(root):
    if "project_plan_v3.yaml" in fs: plan=os.path.join(b,"project_plan_v3.yaml"); break
  doc={}; txt=""; active=None
  if plan and os.path.isfile(plan) and yaml:
    txt=open(plan,"r",encoding="utf-8").read()
    try: doc=yaml.safe_load(txt) or {}
    except Exception: doc={}
  nodes=[]
  for n in _all(doc):
    if isinstance(n,dict):
      _id=str(n.get("id") or n.get("step_id") or "").strip()
      if not _id: continue
      title=str(n.get("name") or n.get("title") or n.get("desc") or "").strip()
      status=str(n.get("status") or n.get("state") or "").strip()
      nodes.append({"id":_id,"title":title,"status":status,"children":[]})
  items={n["id"]:{**n,"children":[]} for n in nodes}
  phases={}
  for sid in sorted(items.keys(), key=_natkey):
    major=sid.split(".",1)[0]
    ph=phases.setdefault(major,{"id":major,"title":"Phase "+str(major),"status":"","children":[]})
    ph["children"].append(items[sid])
  tree=[]; totals={"done":0,"in_progress":0,"blocked":0,"todo":0}
  for major in sorted(phases.keys(), key=_natkey):
    ph=phases[major]; _sum(totals,_count(ph)); tree.append(ph)
  if isinstance(doc,dict): active=doc.get("active_step")
  return {"active":active,"tree":tree,"totals":totals}
