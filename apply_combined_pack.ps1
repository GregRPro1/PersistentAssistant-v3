param(
    [string]$ZipPath,                                     # optional; auto-detects newest PA*.zip in Downloads if omitted
    [string]$RepoRoot = "C:\_Repos\PersistentAssistant"
)

$ErrorActionPreference = 'Stop'

function Fail($m) { Write-Error $m; exit 1 }

function Invoke-Proc([string]$exe, [string]$args) {
    Write-Host ">> $exe $args"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $exe
    $psi.Arguments = $args
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.WaitForExit()
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    if ($out.Trim()) { Write-Host $out.Trim() }
    if ($p.ExitCode -ne 0) {
        if ($err.Trim()) { Write-Host $err.Trim() -ForegroundColor Red }
        Fail "Command failed ($($p.ExitCode)): $exe $args"
    }
}

function Ensure-RepoRoot([string]$root) {
    if (-not (Test-Path (Join-Path $root '.git'))) { Fail "Repo root not found at $root (.git missing)" }
}

function Resolve-Zip([string]$maybe) {
    if ($maybe -and (Test-Path $maybe)) { return (Resolve-Path $maybe).Path }
    $dl = Join-Path $env:USERPROFILE 'Downloads'
    if (-not (Test-Path $dl)) { return $null }
    $cands = Get-ChildItem $dl -File -Filter '*.zip' |
    Where-Object {
        $_.Name -match '^PA_(OUTPUT|INPUT|STARTER).*\.zip$' -or
        $_.Name -match '^PA_.*\.zip$'
    } | Sort-Object LastWriteTime -Descending
    if ($cands.Count -gt 0) { return $cands[0].FullName }
    return $null
}

function Apply-PackZip([string]$PackZip, [string]$Root) {
    Write-Host "=== Applying pack: $PackZip ==="
    Ensure-RepoRoot $Root
    Unblock-File -Path $PackZip -ErrorAction SilentlyContinue
    Expand-Archive -Path $PackZip -DestinationPath $Root -Force

    $apply = Join-Path $Root "scripts\apply_pack.ps1"
    if (Test-Path $apply) {
        Write-Host "Found pack apply script: $apply"
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

function Install-Agents([string]$Staging, [string]$Root) {
    $agentDir = Join-Path $Staging "agent"
    $installAgent = Join-Path $agentDir "install_agent.ps1"
    $installEmail = Join-Path $agentDir "install_email_agent.ps1"
    $applyAnySrc = Join-Path $Staging "scripts\apply_any_pack.ps1"

    if ((Test-Path $installAgent) -or (Test-Path $installEmail)) {
        Write-Host "Installing agents…"
        if (Test-Path $agentDir) {
            Copy-Item -Recurse -Force $agentDir (Join-Path $Root "agent")
        }
        if (Test-Path $applyAnySrc) {
            New-Item -ItemType Directory -Force (Join-Path $Root "scripts") | Out-Null
            Copy-Item -Force $applyAnySrc (Join-Path $Root "scripts\apply_any_pack.ps1")
        }
        $ia = Join-Path $Root "agent\install_agent.ps1"
        if (Test-Path $ia) {
            Invoke-Proc "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$ia`" -RepoRoot `"$Root`""
        }
        $ie = Join-Path $Root "agent\install_email_agent.ps1"
        if (Test-Path $ie) {
            Invoke-Proc "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$ie`" -RepoRoot `"$Root`" -EveryMinutes 1"
        }
    }
}

# --- main ---
Ensure-RepoRoot $RepoRoot

$ResolvedZip = Resolve-Zip $ZipPath
if (-not $ResolvedZip) {
    Write-Warning "No -ZipPath provided or file not found. Scanned Downloads but found no PA_*.zip."
    $dl = Join-Path $env:USERPROFILE 'Downloads'
    if (Test-Path $dl) {
        $top = Get-ChildItem $dl -File -Filter '*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -First 5
        if ($top) {
            Write-Host "`nRecent zips in Downloads:"
            $top | ForEach-Object { Write-Host (" - {0}  ({1})" -f $_.FullName, $_.LastWriteTime) }
        }
    }
    Fail "Place the pack zip in Downloads (prefixed PA_) or pass -ZipPath."
}

Write-Host "Using pack: $ResolvedZip"

# Stage extraction to inspect contents
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$Staging = Join-Path $RepoRoot ("_staging_" + $ts)
New-Item -ItemType Directory -Force $Staging | Out-Null
Unblock-File -Path $ResolvedZip -ErrorAction SilentlyContinue
Expand-Archive -Path $ResolvedZip -DestinationPath $Staging -Force

# 1) Install agents if present
# (skipped) Install-Agents -Staging $Staging -Root $RepoRoot# 2) Apply any nested PA_OUTPUT_*.zip (ordered: PA-102, PA-201, then others)
$nested = @(Get-ChildItem -Path $Staging -Filter "PA_OUTPUT_*.zip" -File -Recurse -ErrorAction SilentlyContinue)
if ($nested.Count -gt 0) {
    $nested = $nested | Sort-Object { if ($_.Name -match 'PA-102') { 0 } elseif ($_.Name -match 'PA-201') { 1 } else { 2 } }, Name
    foreach ($z in $nested) {
        Apply-PackZip -PackZip $z.FullName -Root $RepoRoot
    }
}

# 3) If the combined pack itself looks like a normal pack, apply it too
$rootApply = Join-Path $Staging "scripts\apply_pack.ps1"
if (Test-Path $rootApply) {
    Copy-Item -Recurse -Force (Join-Path $Staging "*") $RepoRoot
    Apply-PackZip -PackZip $ResolvedZip -Root $RepoRoot
}

Write-Host "=== All done ==="



