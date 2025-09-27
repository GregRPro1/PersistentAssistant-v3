import os, yaml
IDS = ["PA-101","PA-102","PA-201","PA-202","PA-203","PA-204","PA-205","PA-206","PA-207","PA-209","PA-210","PA-211","PA-212","PA-213","PA-220","PA-221","PA-222","PA-223","PA-224","PA-225","PA-226","PA-227","PA-230","PA-231"]
def test_plan_has_all_ids():
    p=os.path.join("project","plans","project_plan_v3.yaml"); assert os.path.exists(p), f"missing {p}"
    y=yaml.safe_load(open(p,encoding="utf-8")) or {}; steps={s.get('id') for s in (y.get('dev_steps') or [])}
    missing=[i for i in IDS if i not in steps]; assert not missing, f"dev_steps missing ids: {missing}"
