import json, time
from pathlib import Path

def promote(intake_file: Path, dev_steps_dir: Path) -> Path:
    data = json.loads(Path(intake_file).read_text(encoding='utf-8'))
    ts = time.strftime('%Y%m%d_%H%M')
    step_id = f"PA-9{ts[-2:]}"  # temp id
    out_dir = Path(dev_steps_dir)/step_id; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir/'dev_step.yaml').write_text(
        f"id: {step_id}\ntitle: {data.get('title','Untitled')}\nstatus: proposed\nowner: greg\n",
        encoding='utf-8'
    )
    return out_dir

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--intake', required=True); ap.add_argument('--dev-steps', default='dev_steps')
    a=ap.parse_args(); p=promote(Path(a.intake), Path(a.dev_steps)); print(p)

if __name__=='__main__': main()
