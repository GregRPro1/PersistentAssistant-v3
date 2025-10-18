Param(
    [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\.."),
    [string]$PayloadDir = (Join-Path $PSScriptRoot "..\payload")
)

Write-Host "Applying payload from $PayloadDir to $RepoRoot"

if (-not (Test-Path $PayloadDir)) {
    Write-Host "[FAIL] Payload directory not found: $PayloadDir"
    exit 2
}

# Copy payload contents into repo (preserve structure)
Get-ChildItem -Path $PayloadDir -Recurse | ForEach-Object {
    if (-not $_.PSIsContainer) {
        $rel = $_.FullName.Substring($PayloadDir.Length).TrimStart('\','/')
        $dest = Join-Path $RepoRoot $rel
        New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
        Copy-Item -Path $_.FullName -Destination $dest -Force
    }
}

Write-Host "[OK] Payload applied"
exit 0
