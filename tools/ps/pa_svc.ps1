Set-StrictMode -Version Latest

. "C:\_Repos\PersistentAssistant\tools\ps\pa_diag.ps1"

function Check-PythonCompile { param([string]$FilePath)
  $res = [ordered]@{ file=$FilePath; ok=$false; error='' }
  if (-not (Test-Path -LiteralPath $FilePath)) { $res.error = 'not found'; return $res }
  $tmpE = Join-Path $env:TEMP ('pyc_err_' + [Guid]::NewGuid().ToString('N') + '.txt')
  $tmpO = Join-Path $env:TEMP ('pyc_out_' + [Guid]::NewGuid().ToString('N') + '.txt')
  $LASTEXITCODE = 0
  & python -m py_compile $FilePath 1> $tmpO 2> $tmpE
  if ($LASTEXITCODE -eq 0) { $res.ok = $true } else { if (Test-Path -LiteralPath $tmpE) { $res.error = (Get-Content -LiteralPath $tmpE -Raw) } }
  if (Test-Path -LiteralPath $tmpE) { Remove-Item -LiteralPath $tmpE -Force -ErrorAction SilentlyContinue }
  if (Test-Path -LiteralPath $tmpO) { Remove-Item -LiteralPath $tmpO -Force -ErrorAction SilentlyContinue }
  return $res
}

function Start-ServiceIfNeeded {
  param([int]$Port,[string]$ScriptPath,[string[]]$Args,[string]$LogPath)
  $already = Get-PortPids -Port $Port
  if ($already.Count -gt 0) { Write-Host ('Port {0} already listening (PIDs: {1})' -f $Port, ($already -join ',')); return @{ ok=True; port=$Port; reused=True; pids=@($already) } }
  if (-not (Test-Path -LiteralPath $ScriptPath)) { Write-Host ('Start skipped: {0} not found' -f $ScriptPath); return @{ ok=False; port=$Port; reused=False; pids=@(); reason='script_missing' } }
  $logOut = $LogPath
  $logErr = [IO.Path]::ChangeExtension($LogPath, '.err.log')
  $argList = @($ScriptPath) + $Args
  Ensure-Dir (Split-Path -Parent $LogPath)
  $p = Start-Process -FilePath 'python' -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput $logOut -RedirectStandardError $logErr -WorkingDirectory (Get-Location).Path
  Start-Sleep -Seconds 2
  $pidsAfter = Get-PortPids -Port $Port
  $ok = $pidsAfter.Count -gt 0
  Write-Host ('Start {0} on {1}: {2}' -f $ScriptPath, $Port, (if ($ok) {'OK'} else {'FAIL'}))
  return @{ ok=$ok; port=$Port; reused=False; pids=@($pidsAfter); stdout=$logOut; stderr=$logErr }
}

function Parse-StartupMarkers { param([string]$LogPath)
  $markers = @{ running_on=@(); debugger_pin=@(); bind_errors=@() }
  if (-not (Test-Path -LiteralPath $LogPath)) { return $markers }
  try {
    $txt = Get-Content -LiteralPath $LogPath -Raw -ErrorAction SilentlyContinue
    $lines = $txt -split '\\r?\\n'
    foreach ($ln in $lines) {
      if ($ln -match 'Running on\\s+(http[^\\s]+)') { $markers.running_on += $matches[1] }
      if ($ln -match 'Debugger PIN\\s*:\\s*([A-Za-z0-9\\-]+)') { $markers.debugger_pin += $matches[1] }
      if ($ln -match '(Address already in use|Permission denied|OSError)') { $markers.bind_errors += $ln }
    }
  } catch {}
  return $markers
}
