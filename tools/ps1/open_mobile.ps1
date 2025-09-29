param([string]$BindHost='127.0.0.1',[int]$BindPort=8776)
$ErrorActionPreference='Stop'
$url = "http://$($BindHost):$($BindPort)/app/"
$edge = Get-Command 'msedge.exe' -ErrorAction SilentlyContinue
if ($edge) { Start-Process -FilePath $edge.Source -ArgumentList $url; exit 0 }
$path1 = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$path2 = 'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
if (Test-Path $path1) { Start-Process -FilePath $path1 -ArgumentList $url; exit 0 }
if (Test-Path $path2) { Start-Process -FilePath $path2 -ArgumentList $url; exit 0 }
Start-Process "cmd" "/c start $url"
