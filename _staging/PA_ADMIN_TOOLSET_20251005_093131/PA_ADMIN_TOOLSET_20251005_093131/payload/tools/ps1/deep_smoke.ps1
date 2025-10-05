
param(
  [switch]$Restart,
  [int]$TimeoutSec = 6
)

function Try-Invoke($url, $method = 'GET', $body = $null, $timeout = $TimeoutSec) {
  try {
    if ($method -eq 'GET') {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout
    } else {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeout -Method $method -Body $body
    }
    return @{ ok = $true; code = $r.StatusCode; content = $r.Content }
  } catch {
    return @{ ok = $false; error = $_.Exception.Message }
  }
}

$base = 'http://127.0.0.1:8776'

if ($Restart) {
  pwsh tools\ps1\stop_watchdog.ps1 | Out-Null
  Start-Sleep -Seconds 1
  pwsh tools\ps1\run_watchdog.ps1 | Out-Null
  Start-Sleep -Seconds 2
}

$health = Try-Invoke "$base/healthz"
$debug  = Try-Invoke "$base/__debug"

$routes = @()
$apiPath = $null
$uiPath  = $null
if ($debug.ok) {
  $routes = ($debug.content -split "`r?`n") | Where-Object { $_ -match '^\s*/' } | ForEach-Object { ($_ -replace '\s','') }
  foreach($p in '/api/watchdog','/api/api/watchdog'){ if ($routes -contains $p) { $apiPath = $p; break } }
  foreach($p in '/app/watchdog','/app/app/watchdog'){ if ($routes -contains $p) { $uiPath = $p; break } }
}

$api = $null; $ui = $null
if ($apiPath) { $api = Try-Invoke "$base$apiPath" }
if ($uiPath)  { $ui  = Try-Invoke "$base$uiPath" }

$tunnel = $null
if (Test-Path 'reports\ops\tunnel_url.txt') { $tunnel = (Get-Content 'reports\ops\tunnel_url.txt' -TotalCount 1).Trim() }
$t_health = $null
if ($tunnel) { $t_health = Try-Invoke "$tunnel/healthz" }

$result = [ordered]@{
  when     = (Get-Date).ToString('s')
  healthz  = $health
  routes   = $routes
  apiPath  = $apiPath
  uiPath   = $uiPath
  apiProbe = $api
  uiProbe  = $ui
  tunnel   = $tunnel
  tunnel_health = $t_health
}

New-Item -ItemType Directory -Force 'tmp\logs' | Out-Null
Set-Content -Encoding UTF8 'tmp\logs\deep_smoke_result.json' (([pscustomobject]$result) | ConvertTo-Json -Depth 6)
Write-Host "Deep smoke complete. Saved tmp\logs\deep_smoke_result.json"
