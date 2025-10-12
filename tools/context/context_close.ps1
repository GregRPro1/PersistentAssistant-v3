param(
  [Parameter(Mandatory=$true)][string]$MasterId,
  [Parameter(Mandatory=$true)][string]$ChildId,
  [string]$Notes = ""
)
$ErrorActionPreference='Stop'
$repo = git rev-parse --show-toplevel 2>$null; if (-not $repo){$repo="C:\_Repos\PersistentAssistant"}
$repo = [System.IO.Path]::GetFullPath($repo)
$summaryYaml = Join-Path $repo ("_context\"+$ChildId+"\summary.yaml")
if (-not (Test-Path $summaryYaml)){ Write-Error "Missing summary for $ChildId. Run context_capture.ps1 first."; exit 1 }
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ($Notes){ $Notes.Split("`r`n") | ForEach-Object { Add-Content -LiteralPath $summaryYaml -Value ("  " + $_) -Encoding UTF8 } }
Add-Content -LiteralPath $summaryYaml -Value ("  --- closed at " + $now) -Encoding UTF8
Write-Host "Closed context $ChildId."
