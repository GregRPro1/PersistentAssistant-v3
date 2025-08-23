param([int]$Port=8781,[int]$Every=5,[int]$MaxRestarts=3)
$ErrorActionPreference="SilentlyContinue"
function J { param([string]$Url) try{ Invoke-RestMethod -Uri $Url -TimeoutSec 2 }catch{ $null } }
function Owners { param([int]$Port) @((Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ }) ) }
function BindAddr { param([int]$Port) (netstat -ano -p tcp | Select-String (":$Port ") | ForEach-Object { ($_ -split "\s+" ) | Where-Object {$_} } | Select-Object -First 1) }
$log = Join-Path "tmp\logs" ("watchdog_{0}.log" -f $Port)
for($r=0;$r -le $MaxRestarts;$r++){
  $pLocal = J ("http://127.0.0.1:{0}/phone/ping" -f $Port)
  $lan = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch "^127\." } | Select-Object -First 1 -ExpandProperty IPAddress)
  if(-not $lan){ $lan="127.0.0.1" }
  $pLan = J ("http://{0}:{1}/phone/ping" -f $lan,$Port)
  $bindRaw = BindAddr -Port $Port
  $msg = ("[{0}] local={1} lan={2} bind='{3}'" -f (Get-Date).ToString("HH:mm:ss"), [bool]$pLocal, [bool]$pLan, $bindRaw)
  $msg | Tee-Object -FilePath $log -Append
  if($pLocal -and -not $pLan){
    $owners = Owners -Port $Port
    ("  action: restart; owners={0}" -f ($owners -join ",")) | Tee-Object -FilePath $log -Append
    foreach($pid in $owners){ try{ Stop-Process -Id $pid -Force }catch{}; try{ & taskkill /PID $pid /F /T | Out-Null }catch{} }
    Start-Sleep -Milliseconds 400
    try{ Start-Process -FilePath (Get-Command python).Source -ArgumentList ("server\serve_phone_clean.py {0}" -f $Port) -WorkingDirectory (Get-Location).Path -WindowStyle Hidden | Out-Null }catch{}
    Start-Sleep -Seconds 1
  }
  Start-Sleep -Seconds $Every
}
