#!/usr/bin/env python3
import sys, re, datetime, pathlib

PLAN = r"C:\_Repos\PersistentAssistant\pal_project_plan.yaml"

def set_phase_status(text, pid, status):
    # naive but safe within our structured file
    pattern = rf"(^\s*-\s*id:\s*{re.escape(pid)}\s*$.*?^\s*status:\s*)\w+"
    return re.sub(pattern, rf"\1{status}", text, flags=re.M|re.S)

def set_task_status(text, pid, tid, status):
    # locate phase block, then task block, replace its 'status:' line
    phase_pat = rf"(^\s*-\s*id:\s*{re.escape(pid)}\s*$.*?)(?=^\s*-\s*id:|\Z)"
    m = re.search(phase_pat, text, flags=re.M|re.S)
    if not m: return text
    block = m.group(1)
    task_pat = rf"(^\s*-\s*id:\s*{re.escape(tid)}\s*$.*?^\s*status:\s*)\w+"
    new_block = re.sub(task_pat, rf"\1{status}", block, flags=re.M|re.S)
    return text[:m.start(1)] + new_block + text[m.end(1):]

def main():
    if len(sys.argv) != 3:
        print("usage: mark_task.py <Id> <Status>"); sys.exit(2)
    Id, Status = sys.argv[1], sys.argv[2]
    p = pathlib.Path(PLAN)
    text = p.read_text(encoding="utf-8")
    if "." in Id:
        pid, tid = Id.split(".", 1)
        text = set_task_status(text, pid, tid, Status)
    else:
        text = set_phase_status(text, Id, Status)
    text = re.sub(r"(^last_updated_utc:\s*).*$",
                  rf"\g<1>{datetime.datetime.utcnow().isoformat()}",
                  text, flags=re.M)
    p.write_text(text, encoding="utf-8")
    print(f"Updated {Id} -> {Status}")

if __name__ == "__main__":
    main()
