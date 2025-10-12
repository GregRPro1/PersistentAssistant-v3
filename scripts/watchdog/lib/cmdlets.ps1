Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
  param([string]$LogFile,[string]$Message)
  $ts = Get-Date -Format "u"
  "$ts $Message" | Tee-Object -FilePath $LogFile -Append | Out-Null
}

function Ensure-Dir { param([string]$Path) if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null } }

function Get-Listeners {
  param([int[]]$Ports=@())
  $out=@()
  $net = netstat -ano | Select-String -Pattern "LISTENING"
  foreach ($line in $net) {
    $parts = $line.ToString() -split "\s+" | Where-Object { $_ -ne "" }
    if ($parts.Length -ge 5) {
      $local = $parts[1]; $pid = [int]$parts[-1]
      $portStr = ($local -split ":")[-1]
      if ($portStr -match '^\d+$') {
        $p = [int]$portStr
        if ($Ports.Count -eq 0 -or $Ports -contains $p) { $out += [pscustomobject]@{Port=$p;Pid=$pid;Local=$local} }
      }
    }
  }
  $out
}

function Stop-ByPort { param([int[]]$Ports) foreach($p in $Ports){ $c=Get-Listeners -Ports @($p); foreach($i in $c){ try{ Stop-Process -Id $i.Pid -Force }catch{} } } }

function Stop-ByName { param([string]$NamePattern) Get-Process | Where-Object { $_.Name -match $NamePattern } | ForEach-Object { try{ Stop-Process -Id $_.Id -Force }catch{} } }

function Start-ServiceProcess { param([string]$Cwd,[string]$Command,[string]$LogFile)
  Push-Location $Cwd
  try {
    Write-Log -LogFile $LogFile -Message "Starting: $Command (cwd $Cwd)"
    Start-Process -FilePath "pwsh.exe" -ArgumentList "-NoLogo","-NoProfile","-Command",$Command -WindowStyle Hidden | Out-Null
  } finally { Pop-Location }
}

function Test-Http { param([string]$Url) try{ $h=curl.exe -s -I $Url; if($LASTEXITCODE -eq 0 -and ($h -match "HTTP/")){ return $true } }catch{} $false }
