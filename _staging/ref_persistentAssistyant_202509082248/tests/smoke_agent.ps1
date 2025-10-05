param([string]$Base="http://127.0.0.1:8782",[string]$Token="")
Import-Module "$PSScriptRoot/../tools/pa_harness.psm1" -Force
$tok = if($Token){$Token}else{ Get-TokenFromYaml }
$result = [ordered]@{
  time_utc=(Get-Date).ToUniversalTime().ToString("o")
  base=$Base; token_present=[bool]$tok
  agent_ok=$false; agent_bytes=0
  plan_ok=$false; worker_ok=$false; approvals_ok=$false; plan_groups=0
}
$agent = Invoke-TextAuth "$Base/pwa/agent?cb=$(Get-Random)" $tok
if($agent -and $agent.StatusCode -eq 200){ $result.agent_ok=$true; $result.agent_bytes=[int]$agent.Content.Length }
$plan = Invoke-JsonAuth "$Base/agent/plan" $tok
if($plan){ $result.plan_ok=$true; if($plan.plan -and $plan.plan.tree){ $result.plan_groups=@($plan.plan.tree).Count } }
$work = Invoke-JsonAuth "$Base/agent/worker_status" $tok
if($work){ $result.worker_ok=$true }
$apct = Invoke-JsonAuth "$Base/agent/approvals_count" $tok
if($apct){ $result.approvals_ok=$true }
$result