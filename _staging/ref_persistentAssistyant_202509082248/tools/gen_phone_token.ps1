# Generates a random 256-bit token and prints it. Optionally updates config\phone_approvals.yaml
Param(
  [Parameter(Mandatory=$false)][switch]$UpdateConfig
)
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$token = [Convert]::ToBase64String($bytes).Replace("+","-").Replace("/","_").TrimEnd("=")
Write-Host $token
if ($UpdateConfig) {
  $cfgPath = "config\phone_approvals.yaml"
  if (Test-Path $cfgPath) {
    (Get-Content $cfgPath) -replace 'token:\s*".*"', ('token: "' + $token + '"') | Set-Content $cfgPath
    Write-Host "Updated token in $cfgPath"
  } else {
    Write-Host "Config not found at $cfgPath"
  }
}
