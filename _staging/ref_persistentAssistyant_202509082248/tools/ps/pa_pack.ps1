Set-StrictMode -Version Latest

function Save-Json { param([string]$Path,[object]$Obj,[int]$Depth=12) ($Obj | ConvertTo-Json -Depth $Depth) | Set-Content -LiteralPath $Path -Encoding UTF8 }
function Read-Tail { param([string]$Path,[int]$Lines=200) if (-not (Test-Path -LiteralPath $Path)) { return @() } $c = Get-Content -LiteralPath $Path -Tail $Lines -ErrorAction SilentlyContinue; if ($null -eq $c) { @() } else { $c } }
