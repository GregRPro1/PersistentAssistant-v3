
param([string]$Config = ".\agent\agent_config.yaml")
$ErrorActionPreference='Stop'
function Log($m){ $ts=Get-Date -Format "yyyy-MM-dd HH:mm:ss"; $line="[$ts] $m"; Write-Host $line }
function Exec([string]$c){ Write-Host ">> $c"; $p=Start-Process -NoNewWindow -FilePath "powershell" -ArgumentList "-NoProfile","-ExecutionPolicy Bypass","-Command",$c -PassThru -Wait; if($p.ExitCode -ne 0){ throw "Command failed: $c" } }
$cfg = Get-Content -Path $Config -Raw -Encoding UTF8
function GetVal($k){ ($cfg -split "`n" | ? { $_ -match "^$k:\s*`"(.*)`"" } | % { $Matches[1] })[0] }
$repo=GetVal "repo_root"; $incoming=GetVal "incoming_dir"; $processing=GetVal "processing_dir"; $processed=GetVal "processed_dir"; $failed=GetVal "failed_dir"
$null=New-Item -ItemType Directory -Force $incoming,$processing,$processed,$failed | Out-Null
function WaitStable([string]$p){ $last=-1; $ok=0; for($i=0;$i -lt 30;$i++){ try {$len=(Get-Item $p).Length} catch { Start-Sleep 1; continue}; if($len -eq $last){ $ok++ } else { $ok=0; $last=$len } ; if($ok -ge 5){ return $true }; Start-Sleep 1 }; return $false }
function ProcessZip([string]$z){ $n=[IO.Path]::GetFileName($z); Log "Found $n"; if(-not (WaitStable $z)){ Log "Unstable: $n"; Move-Item -Force $z (Join-Path $failed $n); return }
  $dest=Join-Path $processing $n; Move-Item -Force $z $dest
  & (Join-Path $repo "scripts\apply_any_pack.ps1") -ZipPath $dest -RepoRoot $repo
  if($LASTEXITCODE -eq 0){ Move-Item -Force $dest (Join-Path $processed $n); Log "OK: $n" } else { Move-Item -Force $dest (Join-Path $failed $n); Log "FAILED: $n" }
}
Get-ChildItem $incoming -Filter "*.zip" -File | % { ProcessZip $_.FullName }
$fsw = New-Object System.IO.FileSystemWatcher; $fsw.Path=$incoming; $fsw.Filter="*.zip"; $fsw.EnableRaisingEvents=$true
Register-ObjectEvent $fsw Created -Action { ProcessZip $Event.SourceEventArgs.FullPath } | Out-Null
while($true){ Start-Sleep -Seconds 5 }
