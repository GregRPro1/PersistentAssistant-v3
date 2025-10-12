param([string]C:\_Repos\PersistentAssistant)

if (-not C:\_Repos\PersistentAssistant) {
  C:\_Repos\PersistentAssistant = git rev-parse --show-toplevel 2>
  if (-not C:\_Repos\PersistentAssistant) { C:\_Repos\PersistentAssistant = 'C:\_Repos\PersistentAssistant' }
}
Write-Host ('Repo: ' + C:\_Repos\PersistentAssistant)

 = @(
  Join-Path C:\_Repos\PersistentAssistant 'tunnel_url.txt',
  Join-Path C:\_Repos\PersistentAssistant 'tmp\tunnel_url.txt',
  Join-Path C:\_Repos\PersistentAssistant 'tmp\dev_tunnel_url.txt',
  Join-Path C:\_Repos\PersistentAssistant 'tmp\tracker_tunnel_url.txt',
  Join-Path C:\_Repos\PersistentAssistant 'reports\ops\ops_status.json'
)
foreach ( in ) {
  if (Test-Path ) {
    Write-Host ('[FOUND] ' + )
    try {
       = (Get-Content -LiteralPath  -Raw -ErrorAction SilentlyContinue)
      if () { Write-Host (.Substring(0, [Math]::Min(.Length, 400))) }
    } catch {}
  } else {
    Write-Host ('[MISS ] ' + )
  }
}
