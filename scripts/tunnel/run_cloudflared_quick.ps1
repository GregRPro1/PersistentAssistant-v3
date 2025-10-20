param([switch]$NoNotify)
$ErrorActionPreference="Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ops  = Join-Path $repo "reports\ops"
$tjson = Join-Path $ops "tunnel.json"
$tlog  = Join-Path $ops "cloudflared.log"
New-Item -ItemType Directory -Force -Path $ops | Out-Null
"[$(Get-Date -f s)] START" | Add-Content $tlog

# Find cloudflared
$cloud = Join-Path $PSScriptRoot "cloudflared.exe"
if (!(Test-Path $cloud)) { $cloud = "cloudflared" }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $cloud
$psi.Arguments = "tunnel --no-autoupdate --url http://127.0.0.1:5070"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.CreateNoWindow = $true
$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

$regex = 'https://[a-z0-9\-\.]+(?:\.trycloudflare\.com|\.cfargotunnel\.com)'
$wrote = $false
while (-not $proc.HasExited) {
  foreach($s in @("StandardOutput","StandardError")) {
    while(-not $proc.$s.EndOfStream){
      $line = $proc.$s.ReadLine()
      $line | Add-Content $tlog
      if ($line -match $regex) {
        $hostname = $Matches[0]
        @{hostname=$hostname;updated_ts=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()} |
          ConvertTo-Json | Set-Content -Encoding UTF8 -Path $tjson
        if (-not $NoNotify) { Write-Host "[TUNNEL] $hostname" }
        $wrote = $true
      }
    }
  }
  Start-Sleep -Milliseconds 60
}
if (-not $wrote) {
  @{error="no_hostname_detected"; updated_ts=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()} |
    ConvertTo-Json | Set-Content -Encoding UTF8 -Path $tjson
}
