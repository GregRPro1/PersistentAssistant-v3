param(
  [Parameter(Mandatory=$true)][string]$In,
  [string]$Out = $(Join-Path (Split-Path -Parent $In) ((Split-Path -Leaf $In) + ".fixed.ps1")),
  [switch]$Run
)
$ErrorActionPreference = "Stop"

function Read-All([string]$p){ Get-Content -LiteralPath $p -Raw -Encoding UTF8 }
function Write-Utf8([string]$p,[string]$t){ $enc = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($p,$t,$enc) }

$s = Read-All $In
$issues = @()

# 2.1 Ban inline "=( if(" and "=( try{"
if($s -match "=\s*\(if\("){ $issues += "inline-if-expression"; }
if($s -match "=\s*\(try\{"){ $issues += "inline-try-expression"; }

# 2.2 foreach($pid ...) -> $procId
$s = [regex]::Replace($s, 'foreach\(\s*\$pid(\s|\))', 'foreach($procId$1', 'IgnoreCase')

# 2.3 Ambiguous -f param after Set-Content etc. -> replace with explicit -Format is not valid; avoid -f entirely in PS arguments
#     (We only flag it; not auto-fixing arbitrary formats safely.)
if($s -match '\s- f\s'){ $issues += "ambiguous-minus-f"; }

# 2.4 Compress-Archive with hashtable/object in -Path
if($s -match 'Compress-Archive[^\n\r]+-Path[^\n\r]+\@\{'){ $issues += "compress-archive-object-path"; }

# 2.5 Ensure header+footer Script ID present
if($s -notmatch '^\s*#\s*=====\s*SCRIPT:'){ $issues += "missing-script-header"; }
if($s -notmatch '#\s*=====\s*SCRIPT\s*ID:'){ $issues += "missing-script-footer"; }

Write-Utf8 $Out $s

$ok = ($issues.Count -eq 0)
$result = [pscustomobject]@{ ok=$ok; issues=$issues; input=$In; output=$Out }
$result | ConvertTo-Json -Depth 6 | Write-Output

if($Run){
  if(-not $ok){ Write-Error "Gate refused: $($issues -join ', ')" ; exit 2 }
  & powershell -ExecutionPolicy Bypass -File $Out
}