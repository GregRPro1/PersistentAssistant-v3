param([string]$Step="9.5")
$ErrorActionPreference="Continue"
$plan = Get-ChildItem -Path . -Filter "project_plan_v3.yaml" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if($plan){
  $py = if(Test-Path ".\.venv\Scripts\python.exe"){ ".\.venv\Scripts\python.exe" } else { "python" }
  $code = @"
import sys,yaml,io
p=sys.argv[1]; step=sys.argv[2]
try:
  d=yaml.safe_load(io.open(p,'r',encoding='utf-8').read()) or {}
except Exception:
  d={}
d.setdefault('state',{})
d['active_step']=step
d['state']['current']=step
io.open(p,'w',encoding='utf-8').write(yaml.safe_dump(d,sort_keys=False,allow_unicode=True))
print('OK')
"@
  $tmp="tmp\\run"; if(-not(Test-Path $tmp)){ New-Item -ItemType Directory $tmp | Out-Null }
  $pyf=Join-Path $tmp "plan_sync.py"
  [System.IO.File]::WriteAllText($pyf,$code,[System.Text.UTF8Encoding]::new($false))
  try{ & $py $pyf $plan.FullName $Step | Out-Null; "PLAN: active_step -> $Step" }catch{ "PLAN: sync failed" }
}else{
  "PLAN: project_plan_v3.yaml not found"
}