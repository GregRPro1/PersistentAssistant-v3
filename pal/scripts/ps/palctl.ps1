param(
  [ValidateSet("start","stop","restart","health_check","reload_config","shutdown")]
  [string]$Command,
  [ValidateSet("server","tracker")]
  [string]$Target,
  [string]$Message
)
$reqDir = ".\pal\control\requests"
if (-not (Test-Path $reqDir)) { mkdir -Force $reqDir | Out-Null }
$id = (Get-Date).ToString("yyyyMMdd_HHmmss_fff")
$path = Join-Path $reqDir "$id.json"
$payload = @{
  command = $Command
  target  = $Target
  note    = $Message
}
$payload | ConvertTo-Json | Set-Content $path -Encoding UTF8
Write-Host "Enqueued request $Command $Target → $path"
