param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 8787
)

# If FastAPI app exists later, prefer it:
$fastapi = ".\pal\ui\web\app.py"
$python = "$env:VIRTUAL_ENV\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if (Test-Path $fastapi) {
  # Requires: uvicorn installed in venv
  Write-Host "Starting PAL-Web (FastAPI) on http://$Host`:$Port ..."
  & $python -m uvicorn pal.ui.web.app:app --host $Host --port $Port
  exit $LASTEXITCODE
}

# Temporary placeholder: lightweight health server so scaffold is runnable
Write-Host "Starting placeholder health server on http://$Host`:$Port ..."
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://$Host`:$Port/")
$listener.Start()
try {
  while ($true) {
    $ctx = $listener.GetContext()
    $resp = $ctx.Response
    $path = $ctx.Request.RawUrl
    $body = if ($path -like "/healthz*") { '{"ok":true,"version":"0.1.0"}' } else { "PAL placeholder running" }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $resp.ContentType = "application/json"
    $resp.OutputStream.Write($bytes,0,$bytes.Length)
    $resp.Close()
  }
} finally {
  $listener.Stop()
}
