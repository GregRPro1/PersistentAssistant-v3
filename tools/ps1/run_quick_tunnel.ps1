param(
  [int]$Port = 8776,
  [string]$Host = "127.0.0.1",
  [string]$BinDir = (Join-Path $PSScriptRoot '..\bin'),
  [string]$OutDir = (Join-Path $PSScriptRoot '..\..\reports\ops'),
  [int]$WaitSec = 25
)
$ErrorActionPreference = 'Stop'
function Ensure-Dir([string]$p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function Bin-Path([string]$binDir) {
  $path = Join-Path $binDir 'cloudflared.exe'
  if (-not (Test-Path $path)) { & (Join-Path $PSScriptRoot 'install_cloudflared.ps1') -BinDir $binDir | Out-String | Write-Host }
  return (Join-Path $binDir 'cloudflared.exe')
}
$bin = Bin-Path $BinDir
Ensure-Dir $OutDir
$stdout = Join-Path $OutDir 'cloudflared.out.log'
$stderr = Join-Path $OutDir 'cloudflared.err.log'
$pidFile = Join-Path $OutDir 'cloudflared.pid'
$urlFile = Join-Path $OutDir 'tunnel_url.txt'
if (Test-Path $pidFile) {
  try { $old = (Get-Content $pidFile -Raw).Trim(); if ($old) { Stop-Process -Id [int]$old -Force -ErrorAction SilentlyContinue } } catch {}
  Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
}
$args = @('tunnel','--url',"http://$Host`:$Port",'--metrics','127.0.0.1:8888')
Write-Host ("Launching: {0} {1}" -f $bin, ($args -join ' '))
$ps = Start-Process -FilePath $bin -ArgumentList $args -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -Path $pidFile -Value $ps.Id
$deadline = (Get-Date).AddSeconds($WaitSec)
$publicUrl = $null
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 500
  if (Test-Path $stdout) {
    $txt = Get-Content $stdout -Raw -ErrorAction SilentlyContinue
    if ($txt) {
      $m = Select-String -InputObject $txt -Pattern 'https://[^\s"]+trycloudflare\.com' -AllMatches
      if ($m -and $m.Matches.Count -gt 0) { $publicUrl = $m.Matches[0].Value; break }
    }
  }
}
if (-not $publicUrl) { Write-Error "No tunnel URL found in $stdout; check $stderr for errors."; exit 2 }
Set-Content -Path $urlFile -Value $publicUrl
Write-Host "Tunnel URL: $publicUrl"
exit 0
