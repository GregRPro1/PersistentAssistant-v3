Get-Process | Where-Object { $_.Name -like "cloudflared*" } | ForEach-Object { 
  Write-Host "Stopping $($_.Id) $($_.ProcessName)"; Stop-Process -Id $_.Id -Force
}; Write-Host "Done."
