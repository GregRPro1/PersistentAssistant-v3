
# Apply consolidated learnings for PAL20251013A
$ErrorActionPreference = 'Stop'
Write-Host "=== Applying PAL20251013A_consolidated_learnings_pack ==="

# Resolve repo root
$dst = git rev-parse --show-toplevel 2>$null
if (-not $dst) { $dst = "C:\_Repos\PersistentAssistant" }
$dst = [System.IO.Path]::GetFullPath($dst)

# Paths
$contextDir = Join-Path $dst "_context\PAL20251013A"
$newSummary = Join-Path $contextDir "summary.md"
$indexPath  = Join-Path $dst "_context\PAL20251013\index.yaml"

# Ensure dirs
$null = New-Item -ItemType Directory -Force -Path $contextDir

# Write summary.md from pack payload
$payload = Get-Content -LiteralPath (Join-Path $PSScriptRoot "..\_context\PAL20251013A\summary.md") -Raw -Encoding UTF8
Set-Content -LiteralPath $newSummary -Value $payload -Encoding UTF8
Write-Host "Wrote: $newSummary"

# Best-effort index update (append if exists)
try {
  if (Test-Path $indexPath) {
    $idx = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8
    if ($idx -notmatch "PAL20251013A") {
      Add-Content -LiteralPath $indexPath -Value "`n- child: PAL20251013A`n  status: consolidated" -Encoding UTF8
      Write-Host "Updated index: $indexPath"
    } else {
      Write-Host "Index present: $indexPath (unchanged)"
    }
  }
} catch {}

# Commit
git -C $dst add "_context\PAL20251013A\summary.md" | Out-Null
$pending = git -C $dst diff --cached --name-only
if ($pending) {
  git -C $dst commit -m "PAL20251013A: consolidated learnings applied" | Out-Null
  Write-Host "Committed consolidated learnings."
} else {
  Write-Host "No changes to commit (summary identical)."
}
