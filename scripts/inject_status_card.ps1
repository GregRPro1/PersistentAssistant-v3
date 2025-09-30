$ErrorActionPreference='Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$mob = Join-Path $root 'server\mobile_home.py'
$inj = @"
  <div class="card">
    <h3>Status</h3>
    <div id="status"></div>
  </div>

  <script>
    function dot(ok){ return `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${ok?'#0a0':'#b00'};margin-right:6px"></span>`; }
    async function refreshStatus(){
      try{
        const r = await fetch('/api/status/overview');
        const j = await r.json();
        const c = j.checks;
        const rows = [
          ['Server', c.server.ok],
          ['Mobile', c.mobile.ok],
          ['Control', c.control.ok],
          ['Upload API', c.upload_api.ok],
          ['Jobs API', c.jobs_api.ok],
          ['Pack fetcher', c.pack_fetcher.ok, c.pack_fetcher.age||''],
          ['Email watcher', c.email_watcher.ok, c.email_watcher.age||''],
        ].map(([k,ok,age])=>`<div>${dot(ok)} ${k}${age?(' — '+age):''}</div>`).join('');
        document.getElementById('status').innerHTML = rows;
      }catch(e){ document.getElementById('status').textContent = 'status error'; }
      setTimeout(refreshStatus, 2000);
    }
    refreshStatus();
  </script>
"@

$txt = Get-Content $mob -Raw -Encoding UTF8
if ($txt -notmatch '<h3>Status</h3>') {
  $txt = $txt -replace '(</script>\s*\n\s*<div class="card">\s*\n\s*<a class="btn" href="/control/".*?</div>\s*\n\s*</body>)', ($inj + "`n`$1")
  Set-Content -Path $mob -Value $txt -Encoding UTF8
  Write-Host "Injected Status card into mobile_home.py"
} else {
  Write-Host "Status card already present"
}
