$ErrorActionPreference='Stop'
param([string]$Inbox="_inbox",[string]$Processed="_inbox\processed")
$root = (Get-Location).Path
$inboxPath = Join-Path $root $Inbox
$procPath  = Join-Path $root $Processed
New-Item -ItemType Directory -Force -Path $inboxPath | Out-Null
New-Item -ItemType Directory -Force -Path $procPath  | Out-Null
$log = Join-Path $root 'reports\ops\inbox_apply.log'
function Log($m){ $ts=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'; Add-Content -Path $log -Value "$ts $m" }
$zips = Get-ChildItem -Path $inboxPath -Filter *.zip -ErrorAction SilentlyContinue
if (-not $zips){ Log "no zips in $inboxPath"; exit 0 }
foreach($z in $zips){
  Log "apply $($z.FullName)"
  pwsh -File (Join-Path $root 'apply_packs_only.ps1') -ZipPath $z.FullName | Out-Null
  $ec=$LASTEXITCODE
  if ($ec -ne 0) { Log "apply failed ec=$ec" } else { Log "apply ok" }
  $dest = Join-Path $procPath $z.Name
  $i=1; while (Test-Path $dest){ $dest = Join-Path $procPath ("{0}_{1}{2}" -f $z.BaseName,$i,$z.Extension); $i++ }
  Move-Item $z.FullName $dest -Force
  Log "moved to $dest"
}
