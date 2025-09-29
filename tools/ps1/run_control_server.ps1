param([string]$Host='127.0.0.1',[int]$Port=8776)
$ErrorActionPreference='Stop'
Write-Host "Starting PA Control standalone at http://$Host:$Port/control/"
python (Join-Path $PSScriptRoot '..\py\control_server.py') --host $Host --port $Port
