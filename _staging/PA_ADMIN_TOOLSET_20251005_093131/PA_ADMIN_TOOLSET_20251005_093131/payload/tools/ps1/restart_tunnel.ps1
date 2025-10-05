
function Try-Invoke($url, $method = 'GET', $body = $null, $timeout = 8) {
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

function Detect-Routes($base) {
  $d = Try-Invoke "$base/__debug"
  if (-not $d.ok) { return $null }
  $lines = ($d.content -split "`r?`n")
  $routes = $lines | Where-Object { $_ -match '^\s*/' } | ForEach-Object { ($_ -replace '\s','') }
  foreach($p in '/api/watchdog','/api/api/watchdog'){ if ($routes -contains $p) { return $p } }
  return $null
}

$base = 'http://127.0.0.1:8776'
$apiPath = Detect-Routes $base
if (-not $apiPath) { Write-Host "No API route found."; exit 1 }
$r = Try-Invoke "$base$apiPath/tunnel/restart" 'POST' $null 12
if ($r.ok) { Write-Host "Tunnel restart requested." } else { Write-Host "Tunnel restart failed: $($r.error)" }
