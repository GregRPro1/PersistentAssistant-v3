Param(
  [string]$RepoRoot = "C:\_Repos\PersistentAssistant",
  [int]$LocalPort = 8787,
  [string]$TunnelName = "",
  [string]$TunnelUUID = "",
  [string]$ExpectedHostname = "",
  [string]$HealthUrl = ""
)
$ErrorActionPreference = "Stop"
$OutDir = Join-Path $RepoRoot "logs\cloudflared"; New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"; $log = Join-Path $OutDir "smoke_$stamp.log"
function Log($m){ ("{0:u} {1}" -f (Get-Date), $m) | Tee-Object -FilePath $log -Append }

Log "=== Cloudflared Smoke Test ==="

# 1) Probe local service with retries
$urls = @()
if ($HealthUrl) { $urls += $HealthUrl }
$urls += "http://127.0.0.1:$LocalPort","http://localhost:$LocalPort"
$ok = $false
foreach ($u in $urls) {
  for ($i=1; $i -le 5; $i++) {
    try {
      $resp = curl.exe -s -I $u
      if ($LASTEXITCODE -eq 0 -and ($resp -match "HTTP/")) {
        Log "[OK] Local service responded at $u"
        $ok = $true; break
      } else {
        Log "[RETRY $i/5] No HTTP response from $u"
        Start-Sleep -Seconds 1
      }
    } catch {
      Log "[RETRY $i/5] curl failed for $u: $_"
      Start-Sleep -Seconds 1
    }
  }
  if ($ok) { break }
}
if (-not $ok) { throw "Local service not reachable on any of: $($urls -join ', ')" }

# 2) cloudflared presence
$cf = Get-Command cloudflared -ErrorAction SilentlyContinue; if (-not $cf) { throw "cloudflared not in PATH" }

# 3) Auth/config
$cfHome = Join-Path $env:USERPROFILE ".cloudflared"
$cert = Join-Path $cfHome "cert.pem"; if (Test-Path $cert) { Log "[OK] Found cert.pem" } else { Log "[WARN] Missing cert.pem — run: cloudflared tunnel login" }
$configYml = Join-Path $cfHome "config.yml"; if (Test-Path $configYml){ Log "[OK] Found config.yml"; Get-Content $configYml -Raw | Tee-Object -FilePath $log -Append } else { Log "[WARN] No config.yml found" }

# 4) Tunnels
$tunnelsJson = cloudflared.exe tunnel list --output json 2>&1; try { $tunnels = $tunnelsJson | ConvertFrom-Json } catch { $tunnels = $null }
if ($tunnels){ Log "[OK] Tunnels discovered: $($tunnels.Count)"; foreach($t in $tunnels){ Log (" - {0}  {1}  {2}" -f $t.name,$t.id,$t.createdAt) } } else { Log "[WARN] No tunnels found or parse failure." }

# 5) Run tunnel briefly
$runArgs=@("tunnel","run"); if($TunnelName){$runArgs+=$TunnelName}elseif($TunnelUUID){$runArgs+=$TunnelUUID}else{ Log "[WARN] No tunnel specified; run likely to fail." }
$runLog = Join-Path $OutDir "run_$stamp.txt"; Log "Launching: cloudflared $($runArgs -join ' ')"
$proc = Start-Process -FilePath "cloudflared.exe" -ArgumentList $runArgs -RedirectStandardOutput $runLog -RedirectStandardError $runLog -PassThru
Start-Sleep -Seconds 8
if ($proc.HasExited){ Log "[FAIL] cloudflared exited early. See $runLog"; Get-Content $runLog | Select-Object -First 120 | Tee-Object -FilePath $log -Append; throw "cloudflared did not stay running" } else { Log "[OK] cloudflared running (PID $($proc.Id))." }

# 6) Optional hostname probe
if ($ExpectedHostname){
  try{
    $hdrs = curl.exe -s -I "https://$ExpectedHostname"
    if ($LASTEXITCODE -eq 0 -and ($hdrs -match " 200")){ Log "[OK] Hostname reachable: https://$ExpectedHostname" }
    else { Log "[WARN] Hostname probe not 200"; Log ($hdrs | Out-String) }
  } catch { Log "[WARN] Hostname probe failed: $_" }
}

# 7) Cleanup
Log "Stopping cloudflared PID $($proc.Id)"; Stop-Process -Id $proc.Id -Force
Log "Done. Logs at: $log and $runLog"
Write-Host "=== PACK/STATUS: Smoke test complete. See logs in $OutDir ==="
