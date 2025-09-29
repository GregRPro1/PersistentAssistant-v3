import subprocess, sys, base64
from pathlib import Path

FILES = {
  'tools/ps1/run_unified_server.ps1': b'cGFyYW0oKQokRXJyb3JBY3Rpb25QcmVmZXJlbmNlID0gJ1N0b3AnCgpmdW5jdGlvbiBGaW5kLVJlcG9Sb290KFtzdHJpbmddJHN0YXJ0KSB7CiAgaWYgKFtzdHJpbmddOjpJc051bGxPcldoaXRlU3BhY2UoJHN0YXJ0KSkgewogICAgaWYgKCRQU1NjcmlwdFJvb3QgLWFuZCAkUFNTY3JpcHRSb290LlRyaW0oKSkgeyAkc3RhcnQgPSAkUFNTY3JpcHRSb290IH0KICAgIGVsc2VpZiAoJE15SW52b2NhdGlvbi5NeUNvbW1hbmQuUGF0aCkgeyAkc3RhcnQgPSBTcGxpdC1QYXRoIC1QYXJlbnQgJE15SW52b2NhdGlvbi5NeUNvbW1hbmQuUGF0aCB9CiAgICBlbHNlIHsgJHN0YXJ0ID0gKEdldC1Mb2NhdGlvbikuUGF0aCB9CiAgfQogICRjdXIgPSBSZXNvbHZlLVBhdGggLUxpdGVyYWxQYXRoICRzdGFydAogIGZvciAoJGk9MDsgJGkgLWx0IDEwOyAkaSsrKSB7CiAgICBpZiAoVGVzdC1QYXRoIChKb2luLVBhdGggJGN1ciAnLmdpdCcpKSB7IHJldHVybiAkY3VyIH0KICAgICRwYXJlbnQgPSBTcGxpdC1QYXRoIC1QYXJlbnQgJGN1cgogICAgaWYgKCRwYXJlbnQgLWVxICRjdXIpIHsgYnJlYWsgfQogICAgJGN1ciA9ICRwYXJlbnQKICB9CiAgcmV0dXJuIChHZXQtTG9jYXRpb24pLlBhdGgKfQoKJHJvb3QgPSBGaW5kLVJlcG9Sb290ICRudWxsCldyaXRlLUhvc3QgIlVuaWZpZWQgc2VydmVyIHJvb3Q6ICRyb290IgomIHB5dGhvbiAoSm9pbi1QYXRoICRyb290ICd0b29sc1xweVx1bmlmaWVkX3NlcnZlci5weScpCmV4aXQgJExBU1RFWElUQ09ERQo=',
  'dev_steps/PA-320/dev_step.yaml': b'aWQ6IFBBLTMyMAp0aXRsZTogT3BzIHN0YXR1cyBIVE1MICsgU0hBMjU2IHRvb2xzCnR5cGU6IGZlYXR1cmUKc3RhdHVzOiBwbGFubmVkCm93bmVyOiBhc3Npc3RhbnQKZGVzY3JpcHRpb246IHwKICBBZGQgZG9jcy9vcHMvaW5kZXguaHRtbCBwdWJsaXNoZXIsIHNoYTI1NiBoZWxwZXJzLCBhbmQgaW50ZWdyYXRlIHdpdGggY29udHJvbCBwYWdlLgo=', 'dev_steps/PA-330/dev_step.yaml': b'aWQ6IFBBLTMzMAp0aXRsZTogQ29udHJvbCBVSTogVVJML3RhZyBhcHBseSArIGxvZ3MvaGlzdG9yeQp0eXBlOiBmZWF0dXJlCnN0YXR1czogcGxhbm5lZApvd25lcjogYXNzaXN0YW50CmRlc2NyaXB0aW9uOiB8CiAgVXBncmFkZSBjb250cm9sIHBsYW5lIHdpdGggcGFzdGUgVVJML3RhZyBhcHBseSwgbGl2ZSBsb2dzIChTU0UpLCBhbmQgcnVuIGhpc3RvcnkuCg==', 'dev_steps/PA-341/dev_step.yaml': b'aWQ6IFBBLTM0MQp0aXRsZTogV2ViL01vYmlsZSBzaG9ydGxpc3QKdHlwZTogZmVhdHVyZQpzdGF0dXM6IHBsYW5uZWQKb3duZXI6IGFzc2lzdGFudApkZXNjcmlwdGlvbjogfAogIFJhbmsgaW52ZW50b3J5IHRvIHRvcCBjYW5kaWRhdGVzIGZvciByZXVzZTsgZ2VuZXJhdGUgcmVwb3J0cyBmb3IgdGFyZ2V0aW5nLgo=', 'dev_steps/PA-350/dev_step.yaml': b'aWQ6IFBBLTM1MAp0aXRsZTogVW5pZmllZCBzZXJ2ZXIgaGFybmVzcwp0eXBlOiBmZWF0dXJlCnN0YXR1czogcGxhbm5lZApvd25lcjogYXNzaXN0YW50CmRlc2NyaXB0aW9uOiB8CiAgTW91bnQgZXhpc3RpbmcgRmxhc2sgYXBwcy9ibHVlcHJpbnRzIGJlaGluZCBvbmUgcG9ydCB3aXRoIG9wdGlvbmFsIEJlYXJlciBhdXRoLgo=', 'dev_steps/PA-360/dev_step.yaml': b'aWQ6IFBBLTM2MAp0aXRsZTogUmVwbyB0aWR5IGNsYXNzaWZpZXIKdHlwZTogZmVhdHVyZQpzdGF0dXM6IHBsYW5uZWQKb3duZXI6IGFzc2lzdGFudApkZXNjcmlwdGlvbjogfAogIENsYXNzaWZ5IGFjdGl2ZSB2cyBkZXYgdnMgZGVhZDsgcHJvZHVjZSBtb3ZlciArIHJvbGxiYWNrIGZvciBzYWZlIGFyY2hpdmluZy4K', 'dev_steps/PA-342/dev_step.yaml': b'aWQ6IFBBLTM0Mgp0aXRsZTogQ2xvdWRmbGFyZSBUdW5uZWwgaGVscGVyCnR5cGU6IGZlYXR1cmUKc3RhdHVzOiBwbGFubmVkCm93bmVyOiBhc3Npc3RhbnQKZGVzY3JpcHRpb246IHwKICBTZWN1cmUgcmVtb3RlIGFjY2VzcyB3aXRoIGJlYXJlciB0b2tlbiBnYXRlIGFuZCBvbmUtbGluZSB0dW5uZWwgaGVscGVyLgo=',
  'dev_steps/PA-320/manifest.yaml': b'c3RlcDogUEEtMzIwCmFydGlmYWN0czoKICAtIHByb2plY3QvcGxhbnMvcHJvamVjdF9wbGFuX3YzLnlhbWwK', 'dev_steps/PA-330/manifest.yaml': b'c3RlcDogUEEtMzMwCmFydGlmYWN0czoKICAtIHByb2plY3QvcGxhbnMvcHJvamVjdF9wbGFuX3YzLnlhbWwK', 'dev_steps/PA-341/manifest.yaml': b'c3RlcDogUEEtMzQxCmFydGlmYWN0czoKICAtIHByb2plY3QvcGxhbnMvcHJvamVjdF9wbGFuX3YzLnlhbWwK', 'dev_steps/PA-350/manifest.yaml': b'c3RlcDogUEEtMzUwCmFydGlmYWN0czoKICAtIHByb2plY3QvcGxhbnMvcHJvamVjdF9wbGFuX3YzLnlhbWwK', 'dev_steps/PA-360/manifest.yaml': b'c3RlcDogUEEtMzYwCmFydGlmYWN0czoKICAtIHByb2plY3QvcGxhbnMvcHJvamVjdF9wbGFuX3YzLnlhbWwK', 'dev_steps/PA-342/manifest.yaml': b'c3RlcDogUEEtMzQyCmFydGlmYWN0czoKICAtIHByb2plY3QvcGxhbnMvcHJvamVjdF9wbGFuX3YzLnlhbWwK'
}

def run(a,cwd=None,check=True): subprocess.run(a,cwd=cwd,check=check)
def find_root(start: Path)->Path:
    p=start
    for _ in range(10):
        if (p/'.git').exists(): return p
        if p.parent==p: break
        p=p.parent
    return start

def main():
    here = Path(__file__).resolve()
    root = find_root(here)
    # write files
    for rel,b in FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(b))
    # commit + plan merge
    try: run(['git','checkout','-B','step/PA-351-unified-fix-and-plan'], root)
    except Exception: pass
    run(['git','add','-A'], root, check=False)
    run(['git','commit','-m','PA-351: fix unified runner + add planned steps'], root, check=False)
    pm = root/'tools'/'py'/'plan_merge.py'
    if pm.exists():
        run(['python', str(pm), '--merge-dev-steps'], root, check=False)
        run(['git','add','-A'], root, check=False)
        run(['git','commit','-m','PA-351: merge dev_steps into project_plan_v3.yaml'], root, check=False)
    run(['git','push','-u','origin','step/PA-351-unified-fix-and-plan'], root, check=False)
    print('PA-351 done.')

if __name__=='__main__':
    main()
