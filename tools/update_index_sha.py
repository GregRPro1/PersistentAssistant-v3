# --- PA_ROOT_IMPORT ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- /PA_ROOT_IMPORT ---
import yaml, sys
IDX="project_index.yaml"
KEY_PATH=("project_index","files","project_definition","sha256")

def main():
    with open(IDX,"r",encoding="utf-8") as f:
        d=yaml.safe_load(f)
    cur=d
    for k in KEY_PATH[:-1]:
        cur=cur[k]
    cur[KEY_PATH[-1]]=sys.argv[1]
    with open(IDX,"w",encoding="utf-8") as f:
        yaml.safe_dump(d,f,sort_keys=False)
    print("[INDEX SHA UPDATED] project_definition.sha256 set to", sys.argv[1])

if __name__=="__main__":
    main()
