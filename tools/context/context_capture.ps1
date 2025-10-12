param(
  [Parameter(Mandatory=$true)][string]$MasterId,
  [Parameter(Mandatory=$true)][string]$ChildId,
  [string]$Notes = "",
  [string]$NotesFile = ""
)
$ErrorActionPreference='Stop'
$repo = git rev-parse --show-toplevel 2>$null; if (-not $repo){$repo="C:\_Repos\PersistentAssistant"}
$repo = [System.IO.Path]::GetFullPath($repo)
$masterDir = Join-Path $repo ("_context\"+$MasterId)
$childDir  = Join-Path $repo ("_context\"+$ChildId)
$indexYaml = Join-Path $masterDir "index.yaml"
$summaryYaml = Join-Path $childDir "summary.yaml"
New-Item -ItemType Directory -Force -Path $masterDir | Out-Null
New-Item -ItemType Directory -Force -Path $childDir | Out-Null
$branch = (git -C $repo rev-parse --abbrev-ref HEAD).Trim()
$commit = (git -C $repo rev-parse --short HEAD).Trim()
$settings = Join-Path $repo "config\pal_settings.yaml"
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ($NotesFile -and (Test-Path $NotesFile)){ $notesText = Get-Content -Raw -LiteralPath $NotesFile -Encoding UTF8 } else { $notesText = $Notes }
$sum = @()
$sum += "master_id: $MasterId"
$sum += "child_id: $ChildId"
$sum += "timestamp: $now"
$sum += "repo_root: $repo"
$sum += "git_branch: $branch"
$sum += "git_commit: $commit"
$sum += "settings_path: $settings"
$sum += "lessons: |"
if ($notesText){ ($notesText -split "`r?`n") | ForEach-Object { $sum += ("  " + $_) } } else { $sum += "  (empty)" }
$sum | Set-Content -LiteralPath $summaryYaml -Encoding UTF8
$idx = @()
if (Test-Path $indexYaml){
  $idx = Get-Content $indexYaml -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*last_child\s*:' }
} else {
  $idx += "master_id: $MasterId"
  $idx += "created: $now"
  $idx += "children:"
}
$idx += "  - $ChildId"
$idx += "last_child: $ChildId"
$idx | Set-Content -LiteralPath $indexYaml -Encoding UTF8
Write-Host "Captured: $summaryYaml"; Write-Host "Updated:  $indexYaml"
