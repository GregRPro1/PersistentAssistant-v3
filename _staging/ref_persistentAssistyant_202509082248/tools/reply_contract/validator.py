import sys, io, json, re
FIELD_ORDER = ["PACK","STATUS","NEXT","BRIEF","FS"]

def _lines(s): return [ln for ln in s.replace("\r\n","\n").replace("\r","\n").split("\n")]

def validate_text(txt):
  L=[ln for ln in _lines(txt) if ln.strip()!=""]
  if len(L)<2: return False, {}, "needs PACK and STATUS"
  if not L[0].startswith("PACK:"): return False, {}, "first line must start with PACK:"
  if not L[1].startswith("STATUS:"): return False, {}, "second line must start with STATUS:"
  if not re.match(r"^(OK|WARN|FAIL)\b", L[1][7:].strip()): return False, {}, "STATUS must be OK|WARN|FAIL"
  parsed={"PACK":L[0],"STATUS":L[1]}
  i=2
  def take_block(j):
    acc=[]; k=j
    while k<len(L) and not any(L[k].startswith(x+":") for x in FIELD_ORDER): acc.append(L[k]); k+=1
    return ("\n".join(acc).strip(), k)
  while i<len(L):
    ln=L[i]
    if ln.startswith("NEXT:"):
      body=ln.split(":",1)[1].strip()
      try:
        arr=json.loads(body)
        if not isinstance(arr,list): return False, {}, "NEXT must be array"
        if len(arr)>5: return False, {}, "NEXT ≤ 5"
        if not all(isinstance(x,str) for x in arr): return False, {}, "NEXT items must be strings"
        parsed["NEXT"]=arr
      except Exception: return False, {}, "NEXT JSON parse error"
      i+=1; continue
    if ln.startswith("BRIEF:"):
      first=ln[6:].lstrip(); blk,i=take_block(i+1)
      bl=[x for x in _lines(first+"\n"+blk) if x.strip()!=""]
      if len(bl)>4: return False, {}, "BRIEF ≤ 4 lines"
      parsed["BRIEF"]="\n".join(bl); continue
    if ln.startswith("FS:"):
      first=ln[3:].lstrip(); blk,i=take_block(i+1)
      fs=(first+"\n"+blk).strip(); fsL=[x for x in _lines(fs) if x.strip()!=""]
      if len(fsL)>5: return False, {}, "FS ≤ 5 lines"
      try: fs.encode("ascii")
      except UnicodeEncodeError: return False, {}, "FS ASCII-only"
      parsed["FS"]="\n".join(fsL); continue
    if any(ln.startswith(x+":") for x in ["PACK","STATUS"]): return False, {}, "duplicate PACK/STATUS"
    return False, {}, f"unexpected content at line {i+1}"
  return True, parsed, ""

def validate_json(obj):
  import re
  if not isinstance(obj,dict): return False,"not object"
  if "PACK" not in obj or "STATUS" not in obj: return False,"missing PACK/STATUS"
  if not isinstance(obj["PACK"],str) or not obj["PACK"].startswith("PACK:"): return False,"bad PACK"
  if not isinstance(obj["STATUS"],str) or not re.match(r"^STATUS:\s+(OK|WARN|FAIL)\b", obj["STATUS"]): return False,"bad STATUS"
  if "NEXT" in obj:
    a=obj["NEXT"]
    if not isinstance(a,list) or any(not isinstance(x,str) for x in a) or len(a)>5: return False,"bad NEXT"
  if "BRIEF" in obj and not isinstance(obj["BRIEF"],str): return False,"bad BRIEF"
  if "FS" in obj:
    s=obj["FS"]
    if not isinstance(s,str): return False,"bad FS"
    if len([ln for ln in s.splitlines() if ln.strip()!=""])>5: return False,"FS lines>5"
    try: s.encode("ascii")
    except UnicodeEncodeError: return False,"FS non-ASCII"
  return True,""

def rewrite_to_schema(free):
  bl=[ln.strip() for ln in free.splitlines() if ln.strip()!=""][:4]
  out=["PACK: [NOT CREATED]","STATUS: WARN (autofixed to schema)"]
  if bl: out.append("BRIEF: "+bl[0]); out.extend(bl[1:])
  return "\n".join(out)

if __name__=="__main__":
  import argparse, json
  ap=argparse.ArgumentParser()
  ap.add_argument("mode", choices=["text","json","rewrite","sample"])
  ap.add_argument("path"); ap.add_argument("out", nargs="?")
  a=ap.parse_args()
  if a.mode=="text":
    s=io.open(a.path,"r",encoding="utf-8").read()
    ok,parsed,reason=validate_text(s)
    print(json.dumps({"ok":ok,"reason":reason,"parsed":parsed}, ensure_ascii=False)); sys.exit(0 if ok else 3)
  if a.mode=="json":
    obj=json.load(io.open(a.path,"r",encoding="utf-8"))
    ok,reason=validate_json(obj)
    print(json.dumps({"ok":ok,"reason":reason}, ensure_ascii=False)); sys.exit(0 if ok else 3)
  if a.mode=="rewrite":
    s=io.open(a.path,"r",encoding="utf-8").read()
    out=rewrite_to_schema(s); io.open(a.out,"w",encoding="utf-8").write(out); print(a.out); sys.exit(0)
  if a.mode=="sample":
    sample="PACK: C:\\\\_Repos\\\\PersistentAssistant\\\\tmp\\\\feedback\\\\pack_demo.zip\nSTATUS: OK (demo)\nNEXT: [\"9.6-P0\",\"9.5a\"]\nBRIEF: Demo compliant reply"
    io.open(a.path,"w",encoding="utf-8").write(sample); print(a.path); sys.exit(0)
