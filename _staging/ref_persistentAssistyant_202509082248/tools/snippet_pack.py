from __future__ import annotations
import pathlib, textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
SNIP = ROOT/"tmp"/"snippets"; SNIP.mkdir(parents=True, exist_ok=True)

def write(name, body):
    (SNIP/name).write_text(textwrap.dedent(body).lstrip()+"\n", encoding="utf-8")

write("run_window.ps1", r"""
python gui\run_window.py
""")

write("leb_run_example.ps1", r"""
python tools\leb_runner.py -- python tools\show_next_step.py
""")

write("safe_replace_example.ps1", r"""
$sha = (Get-FileHash gui\tabs\chat_tab.py -Algorithm SHA256).Hash
python tools\safe_replace.py --path gui\tabs\chat_tab.py --expected-sha $sha --new tmp\chat_tab_fixed.py
""")

write("plan_show.ps1", r"""
python tools\show_next_step.py
""")

print("[SNIPPETS OK]", SNIP)
