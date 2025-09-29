param([string]$Host='127.0.0.1',[int]$Port=8776)
$ErrorActionPreference='Stop'
$u = "http://$($Host):$($Port)/control/"
Write-Host "Starting PA Control standalone at $u"
python (Join-Path $PSScriptRoot '..\py\control_server.py') --host $Host --port $Port
