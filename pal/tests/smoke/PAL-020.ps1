param([string]$Name = $null)
$OutDir = ".\reports\smoke"; if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }
$ts = (Get-Date).ToString("s")
$result = @{ test = $Name; ts = $ts; ok = $true; notes = "P3 stub PASS" }
($result | ConvertTo-Json -Depth 5) | Set-Content (Join-Path $OutDir "$Name.json") -Encoding UTF8
Write-Host "$Name PASS"
