param(
    [string]$ZipPath,                                     # optional; auto-picks newest PA*.zip in Downloads
    [string]$RepoRoot = "C:\_Repos\PersistentAssistant"
)

$ErrorActionPreference = 'Stop'
function Fail($m) { Write-Error $m; exit 1 }
function Ensure-RepoRoot([string]$root) { if (-not (Test-Path (Join-Path $root '.git'))) { Fail "Repo root not found at $root (.git missing)" } }

function Resolve-Zip([string]$maybe) {
    if ($maybe -and (Test-Path $maybe)) { return (Resolve-Path $maybe).Path }
    $dl = Join-Path $env:USERPROFILE 'Downloads'
    if (-not (Test-Path $dl)) { return $null }
    $cands = Get-ChildItem $dl -File -Filter '*.zip' |
    Where-Object { $_.Name -match '^PA_(OUTPUT|INPUT|STARTER).*\.zip$' -or $_.Name -match '^PA_.*\.zip$' } |
    Sort-Object LastWriteTime -Descending
    if ($cands.Count -gt 0) { return $cands[0].FullName }
    return $null
}

function Apply-PackZip([string]$PackZip, [string]$Root) {
    Write-Host "=== Applying pack: $PackZip ==="
    Unblock-File -Path $PackZip -ErrorAction SilentlyContinue
    Expand-Archive -Path $PackZip -DestinationPath $Root -Force

    $apply = Join-Path $Root "scripts\apply_pack.ps1"
    if (Test-Path $apply) {
        Write-Host "Found scripts\apply_pack.ps1 — running it..."
        & $apply
        if ($LASTEXITCODE -ne 0) { Fail "apply_pack.ps1 failed with exit code $LASTEXITCODE" }
        return
    }

    $runner = Join-Path $Root "tools\ps1\run_smoke.ps1"
    if (Test-Path $runner) {
        $devStepsRoot = Join-Path $Root "dev_steps"
        $dirs = @(Get-ChildItem -Path $devStepsRoot -Directory -ErrorAction SilentlyContinue)
        if (-not $dirs -or $dirs.Count -eq 0) { Fail "No dev_steps/* found after extraction; cannot run smoke fallback." }
        $StepId = $dirs[0].Name
        Write-Host "Fallback: running smoke for StepId=$StepId"
        & $runner -StepId $StepId
        if ($LASTEXITCODE -ne 0) { Fail "run_smoke.ps1 failed with exit code $LASTEXITCODE" }
        return
    }

    Fail "Neither scripts\apply_pack.ps1 nor tools\ps1\run_smoke.ps1 found after extraction."
}

# --- main ---
Ensure-RepoRoot $RepoRoot
$ResolvedZip = Resolve-Zip $ZipPath
if (-not $ResolvedZip) {
    Fail "No pack found. Put the combined pack in Downloads (prefixed PA_) or pass -ZipPath."
}
Write-Host "Using pack: $ResolvedZip"

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$Staging = Join-Path $RepoRoot ("_staging_" + $ts)
New-Item -ItemType Directory -Force $Staging | Out-Null
Unblock-File -Path $ResolvedZip -ErrorAction SilentlyContinue
Expand-Archive -Path $ResolvedZip -DestinationPath $Staging -Force

# Apply nested PA_OUTPUT_*.zip (ordered: PA-102, PA-201, then others)
$nested = @(Get-ChildItem -Path $Staging -Filter "PA_OUTPUT_*.zip" -File -Recurse -ErrorAction SilentlyContinue)
if ($nested.Count -gt 0) {
    $nested = $nested | Sort-Object { if ($_.Name -match 'PA-102') { 0 } elseif ($_.Name -match 'PA-201') { 1 } else { 2 } } , Name
    foreach ($z in $nested) { Apply-PackZip -PackZip $z.FullName -Root $RepoRoot }
}
else {
    # If the combined pack itself is just a normal pack (has scripts/apply_pack.ps1), apply it
    if (Test-Path (Join-Path $Staging "scripts\apply_pack.ps1")) {
        Copy-Item -Recurse -Force (Join-Path $Staging "*") $RepoRoot
        Apply-PackZip -PackZip $ResolvedZip -Root $RepoRoot
    }
    else {
        Fail "No nested PA_OUTPUT_*.zip found and no root apply script."
    }
}

Write-Host "=== Packs applied ==="
