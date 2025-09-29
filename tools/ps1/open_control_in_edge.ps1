param([string]$Host='127.0.0.1',[int]$Port=8776)
$ErrorActionPreference='Stop'
$url = "http://$($Host):$($Port)/control/"
# Try msedge.exe first
$edge = Get-Command 'msedge.exe' -ErrorAction SilentlyContinue
if ($edge) {
  Start-Process -FilePath $edge.Source -ArgumentList $url
  exit 0
}
# Try typical install path
$path1 = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$path2 = 'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
if (Test-Path $path1) { Start-Process -FilePath $path1 -ArgumentList $url; exit 0 }
if (Test-Path $path2) { Start-Process -FilePath $path2 -ArgumentList $url; exit 0 }
# Fallback to shell
Start-Process "cmd" "/c start $url"
