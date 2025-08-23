Param(
  [Parameter(Mandatory=$false)][string]$RepoRoot = "."
)
# Unpack everything into $RepoRoot, keeping structure. This script does not overwrite existing files unless -Force is used by the caller.
Write-Host "Applying pack into $RepoRoot"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item -Path (Join-Path $here "..\server\phone_blueprint.py") -Destination (Join-Path $RepoRoot "server\phone_blueprint.py") -Force
Copy-Item -Path (Join-Path $here "..\server\logs_tail.py") -Destination (Join-Path $RepoRoot "server\logs_tail.py") -Force
Copy-Item -Path (Join-Path $here "..\web\pwa") -Destination (Join-Path $RepoRoot "web\") -Recurse -Force
if (-not (Test-Path (Join-Path $RepoRoot "config\phone_approvals.yaml"))) {
  Copy-Item -Path (Join-Path $here "..\config\phone_approvals.sample.yaml") -Destination (Join-Path $RepoRoot "config\phone_approvals.yaml")
  Write-Host "Created config\phone_approvals.yaml (sample). Update the token."
} else {
  Write-Host "config\phone_approvals.yaml already exists; not overwritten."
}
Write-Host "Apply complete. Next: register blueprint in your Flask app and run port 8770."
