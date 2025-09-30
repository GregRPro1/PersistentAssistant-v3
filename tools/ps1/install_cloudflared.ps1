$ErrorActionPreference = 'Stop'
param([string]$BinDir = (Join-Path $PSScriptRoot '..\bin'))
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Force -Path $BinDir | Out-Null }
$exe = Join-Path $BinDir 'cloudflared.exe'
if (Test-Path $exe) { Write-Host "cloudflared already present at $exe"; exit 0 }
$uri = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
$tmp = Join-Path $env:TEMP ('cloudflared_' + [guid]::NewGuid().ToString() + '.exe')
Write-Host "Downloading cloudflared from $uri ..."
Invoke-WebRequest -Uri $uri -OutFile $tmp -UseBasicParsing
Move-Item -Force -Path $tmp -Destination $exe
Write-Host "cloudflared installed to $exe"
exit 0
