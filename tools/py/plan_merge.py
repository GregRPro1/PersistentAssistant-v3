import sys, yaml
from pathlib import Path
def load_yaml(p):
    if not Path(p).exists(): return {}
    with open(p,'r',encoding='utf-8') as f: return yaml.safe_load(f) or {}
def dump_yaml(obj,p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p,'w',encoding='utf-8') as f: yaml.safe_dump(obj,f,sort_keys=False,allow_unicode=True)
def merge_steps(existing,to_add):
    by_id={s.get('id'):s for s in (existing or []) if isinstance(s,dict) and s.get('id')}
    for s in to_add or []:
        sid=s.get('id'); 
        if not sid: continue
        if sid in by_id:
            m=by_id[sid].copy()
            for k,v in s.items():
                if k=='status' and m.get('status','').lower() not in ('proposed',''): continue
                m[k]=v
            by_id[sid]=m
        else:
            by_id[sid]=s
    return [by_id[k] for k in sorted(by_id.keys(), key=lambda k:(int(''.join([c for c in k if c.isdigit()]) or 0),k))]
def main(plan="project/plans/project_plan_v3.yaml", add="dev_steps/PA-102/plan_steps_to_add.yaml"):
    plan_y=load_yaml(plan); add_y=load_yaml(add)
    plan_y.setdefault('schema_version',3)
    exts=plan_y.get('extensions') or []
    for x in ('dev_steps','ci_policy','board'):
        if x not in exts: exts.append(x)
    plan_y['extensions']=exts
    plan_steps=plan_y.get('dev_steps') or []
    plan_y['dev_steps']=merge_steps(plan_steps, add_y.get('dev_steps'))
    plan_y.setdefault('ci_policy',{}); plan_y.setdefault('board',{})
    dump_yaml(plan_y, plan)
    print("Updated", plan)
if __name__=="__main__":
    try: import yaml as _y
    except ImportError: print("PyYAML required", file=sys.stderr); sys.exit(2)
    plan = sys.argv[1] if len(sys.argv)>1 else "project/plans/project_plan_v3.yaml"
    add  = sys.argv[2] if len(sys.argv)>2 else "dev_steps/PA-102/plan_steps_to_add.yaml"
    main(plan, add)
