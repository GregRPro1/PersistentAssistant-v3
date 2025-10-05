"""preflight_parser v1.1: lint & lightly fix common PowerShell paste hazards."""
import re, sys, json

def load(p): return open(p,"r",encoding="utf-8").read()
def save(p,s): open(p,"w",encoding="utf-8").write(s)

def fix_pid_loop(s):
    # foreach($pid in ...) => $procId
    return re.sub(r"foreach\(\s*\$pid(\s|\))","foreach($procId\\1", s, flags=re.IGNORECASE)

def flag_inline_try_if(s, issues):
    for m in re.finditer(r"=\s*\(if\(", s, flags=re.IGNORECASE):
        issues.append({"kind":"inline_if_expr","at":m.start()})
    for m in re.finditer(r"=\s*\(try\{", s, flags=re.IGNORECASE):
        issues.append({"kind":"inline_try_expr","at":m.start()})
    return s

def fix_compress_archive_args(s, issues):
    # Warn if -Path contains hashtable/object rather than path strings
    for m in re.finditer(r"Compress-Archive[^\n]*-Path[^\n]*@\{", s, flags=re.IGNORECASE):
        issues.append({"kind":"bad_compress_path_object","at":m.start()})
    return s

def run(pin, pout):
    s = load(pin)
    issues=[]
    s = fix_pid_loop(s)
    s = fix_compress_archive_args(s, issues)
    s = flag_inline_try_if(s, issues)
    save(pout, s)
    return {"ok": True, "issues": issues, "in": pin, "out": pout}

if __name__ == "__main__":
    pin=sys.argv[1]; pout=sys.argv[2]
    print(json.dumps(run(pin,pout)))