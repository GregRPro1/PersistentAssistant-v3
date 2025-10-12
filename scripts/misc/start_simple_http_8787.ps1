Param([int]$Port = 8787)
Write-Host "Starting simple HTTP server on 127.0.0.1:$Port (Ctrl+C to stop)"
python -m http.server $Port --bind 127.0.0.1
