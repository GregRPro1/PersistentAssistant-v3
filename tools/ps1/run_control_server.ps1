param([string]$BindHost='127.0.0.1',[int]$BindPort=8776)
$ErrorActionPreference='Stop'
$u = "http://$($BindHost):$($BindPort)/control/"
Write-Host "Starting PA Control standalone at $u"
python (Join-Path $PSScriptRoot '..\py\control_server.py') --host $BindHost --port $BindPort
