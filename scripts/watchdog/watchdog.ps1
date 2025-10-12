Param(
  [ValidateSet('start','stop','restart','status','killports','run')][string]$Action='run',
  [string]$ConfigPath="C:\_Repos\PersistentAssistant\watchdog\watchdog.json"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Write-Log { param([string]$LogFile,[string]$Message) $ts = Get-Date -Format "u"; "$ts $Message" | Tee-Object -FilePath $LogFile -Append | Out-Null }
function Ensure-Dir { param([string]$Path) if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null } }
function Get-Listeners { param([int[]]$Ports=@()) $out=@(); $net = netstat -ano | Select-String -Pattern "LISTENING"; foreach ($line in $net) { $parts = $line.ToString() -split "\s+" | Where-Object { $_ -ne "" }; if ($parts.Length -ge 5) { $local = $parts[1]; $pid = [int]$parts[-1]; $portStr = ($local -split ":")[-1]; if ($portStr -match '^\d+$') { $p = [int]$portStr; if ($Ports.Count -eq 0 -or $Ports -contains $p) { $out += [pscustomobject]@{Port=$p;Pid=$pid;Local=$local} } } } } $out }
function Stop-ByPort { param([int[]]$Ports) foreach($p in $Ports){ $c=Get-Listeners -Ports @($p); foreach($i in $c){ try{ Stop-Process -Id $i.Pid -Force }catch{} } } }
function Stop-ByName { param([string]$NamePattern) Get-Process | Where-Object { $_.Name -match $NamePattern } | ForEach-Object { try{ Stop-Process -Id $_.Id -Force }catch{} } }
function Start-ServiceProcess { param([string]$Cwd,[string]$Command,[string]$LogFile) Push-Location $Cwd; try { Write-Log -LogFile $LogFile -Message "Starting: $Command (cwd $Cwd)"; Start-Process -FilePath "pwsh.exe" -ArgumentList "-NoLogo","-NoProfile","-Command",$Command -WindowStyle Hidden | Out-Null } finally { Pop-Location } }
function Test-Http { param([string]$Url) try{ $h=curl.exe -s -I $Url; if($LASTEXITCODE -eq 0 -and ($h -match "HTTP/")){ return $true } }catch{} $false }
if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$repoRoot = "C:\_Repos\PersistentAssistant"
$logDir = Join-Path $repoRoot $config.watchdog.log_dir
Ensure-Dir $logDir
$log = Join-Path $logDir ("watchdog_{0}.log" -f (Get-Date -Format "yyyyMMdd"))
$mutexName = $config.watchdog.mutex_name
$poll = [int]$config.watchdog.poll_seconds
$services = $config.services
function SvcPorts($svc){ @($svc.ports | ForEach-Object {[int]$_}) }
function Start-Svc($svc){ $ports = SvcPorts $svc; if ($ports.Count -gt 0) { Stop-ByPort -Ports $ports }; Start-ServiceProcess -Cwd $svc.start.cwd -Command $svc.start.command -LogFile $log }
function Stop-Svc($svc){ $ports = SvcPorts $svc; if ($ports.Count -gt 0) { Stop-ByPort -Ports $ports }; if ($svc.name -eq 'cloudflared') { Stop-ByName -NamePattern "cloudflared" }; if ($svc.name -eq 'pal-dev-server') { Stop-ByName -NamePattern "python" } }
function Health-Ok($svc){ $u="$($svc.health.url)"; if(-not $u){return $true}; return (Test-Http -Url $u) }
switch ($Action) {
  'killports' { $ports = @(); foreach($s in $services){ $ports += (SvcPorts $s) }; $ports = $ports | Sort-Object -Unique; if($ports.Count -gt 0){ Stop-ByPort -Ports $ports }; Write-Host "=== PACK/STATUS: killports done ==="; exit 0 }
  'start'     { foreach($s in $services){ Start-Svc $s }; Write-Host "=== PACK/STATUS: start requested ==="; exit 0 }
  'stop'      { foreach($s in $services){ Stop-Svc $s }; Write-Host "=== PACK/STATUS: stop requested ==="; exit 0 }
  'restart'   { foreach($s in $services){ Stop-Svc $s }; Start-Sleep -Seconds 1; foreach($s in $services){ Start-Svc $s }; Write-Host "=== PACK/STATUS: restart requested ==="; exit 0 }
  'status'    { foreach($s in $services){ "{0,-16} ports=[{1}] health={2}" -f $s.name, ((SvcPorts $s) -join ','), (Health-Ok $s) }; exit 0 }
}
$created=$false
$mtx = New-Object System.Threading.Mutex($false, $mutexName, [ref]$created)
if (-not $created) { Write-Host "Watchdog already running (mutex: $mutexName)"; exit 0 }
Write-Log -LogFile $log -Message "Watchdog started (mutex: $mutexName)"
try {
  while ($true) {
    foreach($s in $services){
      if(-not (Health-Ok $s)){
        Write-Log -LogFile $log -Message ("{0}: health failed; (re)starting" -f $s.name)
        Start-Svc $s
      }
    }
    Start-Sleep -Seconds $poll
  }
} finally {
  $mtx.ReleaseMutex() | Out-Null
  Write-Log -LogFile $log -Message "Watchdog stopped"
}
