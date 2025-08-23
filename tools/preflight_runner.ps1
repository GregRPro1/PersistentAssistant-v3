param([int]$Port=8781, [string]$Token="", [switch]$EnsureFiles, [switch]$Pack)
$ErrorActionPreference="Continue"
function J { param([string]$Url,[int]$t=4) try{ Invoke-RestMethod -Uri $Url -TimeoutSec $t }catch{ $null } }
function Owners { param([int]$Port) @((Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ }) ) }
function BindOK { param([int]$Port) (netstat -ano -p tcp | Select-String (":$Port ") | Select-String ("0.0.0.0:$Port")) -ne $null }
$apprDir=Join-Path (Get-Location).Path "tmp\phone\approvals"; if(-not(Test-Path $apprDir)){ New-Item -ItemType Directory -Path $apprDir | Out-Null }
$base="http://127.0.0.1:{0}" -f $Port
for($i=20;$i -ge 0;$i--){ $pong=J "$base/phone/ping"; Write-Host ("Wait {0}s ping={1}" -f $i,[bool]$pong); if($pong){ break }; Start-Sleep -Milliseconds 300 }
$bind=BindOK -Port $Port; Write-Host ("BIND 0.0.0.0:{0} = {1}" -f $Port,[bool]$bind)
$routes = J "$base/__routes__"; if($routes){ "ROUTES: " + ($routes.routes -join ", ") | Write-Host } else { "ROUTES: [none]" | Write-Host }
$pre=(Get-ChildItem $apprDir -File -ErrorAction SilentlyContinue | Measure-Object).Count
$status=$null; $body=$null
try{ $ts=[int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); $nonce=[guid]::NewGuid().Guid; $payload=@{ action="APPROVE_NEXT"; data=$null; timestamp=$ts; nonce=$nonce } | ConvertTo-Json; $resp=Invoke-WebRequest -Method Post -Uri "$base/phone/approve" -Headers @{Authorization=("Bearer "+$Token);"Content-Type"="application/json"} -Body $payload -TimeoutSec 6; $status=$resp.StatusCode; $body=$resp.Content }catch{ $ex=$_.Exception; try{ $status=$ex.Response.StatusCode.value__ }catch{}; try{ $sr=New-Object System.IO.StreamReader($ex.Response.GetResponseStream()); $body=$sr.ReadToEnd() }catch{} }
Start-Sleep -Milliseconds 300
$post=(Get-ChildItem $apprDir -File -ErrorAction SilentlyContinue | Measure-Object).Count; $delta=$post-$pre
Write-Host ("APPROVE STATUS: {0}" -f $status); Write-Host ("DELTA: {0}" -f $delta)
$ok=([bool](J "$base/phone/ping") -and $bind -and $status -eq 200 -and $delta -gt 0)
if($ok){ "STATUS: OK (preflight verified, bind asserted)" } else { "STATUS: WARN (preflight incomplete; check bind/routes/approve)" }
